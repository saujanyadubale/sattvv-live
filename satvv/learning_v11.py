"""Local experiment memory + supervised next-test ranking, SAT-V&V v1.1.

Evidence-only labels; no injected mechanisms, future observations or oracle fields.
Training/validation are grouped by seed and models are never fitted during runs.
Synthetic classification scores are NOT calibrated spacecraft probabilities.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

DB_PATH = Path('results/learning_v11/campaigns.sqlite3')
MODEL_DIR = Path('results/learning_v11/models')
FEATURE_NAMES = ('test_number','test_cost_min','test_criticality','elapsed_min',
 'bus_voltage_v','bus_current_a','temperature_c','sensor_delta_c','packet_loss_fraction',
 'battery_soc_pct','operating_mode_encoded','requirement_age_proxy','test_repeat_count',
 'bus_minus_nominal_voltage_v')
TRAIN_POLICIES = ('predictive_active','predictive_coverage','predictive_ml_coverage')

def pretest_features(obs, test, ages, repeats):
    from .learned_v09 import feature_row
    from math import isfinite
    # Causal proxy for the time since a requirement was last checked.
    age=sum(min(3.0,max(0.,(obs['time_s']-ages[r])/360.)) for r in test.checks if r in ages)/max(1,len(test.checks))
    values=[float(z) for z in feature_row(obs,test,age,repeats.get(test.id,0))]
    if len(values)!=len(FEATURE_NAMES) or not all(isfinite(v) for v in values):
        raise ValueError('Invalid causal feature vector')
    return values

def _connect(path=DB_PATH):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(str(path),timeout=20)
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=20000')
    db.executescript('''CREATE TABLE IF NOT EXISTS campaigns(
       key TEXT PRIMARY KEY, seed INTEGER NOT NULL, difficulty TEXT NOT NULL,
       intensity TEXT NOT NULL, budget_min INTEGER NOT NULL, policy TEXT NOT NULL,
       stop_on_failure INTEGER NOT NULL, model_id TEXT NOT NULL,
       stored_utc TEXT NOT NULL, detected INTEGER NOT NULL, audit_passed INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS training_rows(
       campaign_key TEXT NOT NULL REFERENCES campaigns(key), step INTEGER NOT NULL,
       test_id TEXT NOT NULL, features TEXT NOT NULL,
       result TEXT NOT NULL CHECK(result IN ('PASS','FAIL','INCONCLUSIVE')),
       PRIMARY KEY(campaign_key,step)
    );
    CREATE INDEX IF NOT EXISTS training_campaign_idx ON training_rows(campaign_key);
    ''')
    return db

def store_run(full_result, db_path=DB_PATH):
    if not full_result['audit']['passed']:
        raise ValueError('Refusing to persist campaign with failed evidence audit')
    m=full_result['meta']; policies=(m['policy'],m['seed'],m['budget_min'],m['challenge_level'],m['challenge_intensity'],m['stop_on_first_failure'],m.get('learning_model_id','frozen'))
    key=hashlib.sha256(json.dumps(policies,sort_keys=True).encode()).hexdigest()[:32]
    evidence=full_result['evidence']
    for rec in evidence:
        row=rec.get('learning_pretest')
        if not row or len(row)!=len(FEATURE_NAMES):
            raise ValueError('Missing causal features in executed test record')
        if rec['status'] not in ('PASS','FAIL','INCONCLUSIVE'):
            raise ValueError('Invalid test outcome')
    with _connect(db_path) as db:
        before=db.total_changes
        db.execute('''INSERT OR IGNORE INTO campaigns VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(
            key,int(m['seed']),m['challenge_level'],m['challenge_intensity'],m['budget_min'],
            m['policy'],int(m['stop_on_first_failure']),m.get('learning_model_id','frozen'),
            datetime.now(timezone.utc).isoformat(),int(full_result['detected']),1))
        inserted=(db.total_changes>before)
        if inserted:
            db.executemany('INSERT INTO training_rows VALUES (?,?,?,?,?)',((
                key,i,rec['test_id'],json.dumps(rec['learning_pretest'],allow_nan=False),rec['status'])
                for i,rec in enumerate(evidence)))
    return inserted

def database_status(db_path=DB_PATH):
    with _connect(db_path) as db:
        camps=db.execute('SELECT COUNT(*),COUNT(DISTINCT seed) FROM campaigns').fetchone()
        rows=db.execute('SELECT COUNT(*),SUM(result="FAIL"),SUM(result="PASS") FROM training_rows').fetchone()
        eligible=db.execute('''SELECT COUNT(DISTINCT c.seed), COUNT(r.step),SUM(r.result='FAIL')
            FROM training_rows r JOIN campaigns c ON c.key=r.campaign_key
            WHERE c.policy IN (?,?,?) AND r.result!='INCONCLUSIVE' ''',TRAIN_POLICIES).fetchone()
    return {'campaigns':camps[0] or 0,'unique_seeds':camps[1] or 0,
            'tests_logged':rows[0] or 0,'fail_samples':rows[1] or 0,'pass_samples':rows[2] or 0,
            'eligible_seeds':eligible[0] or 0,'eligible_samples':eligible[1] or 0,
            'eligible_fail_samples':eligible[2] or 0}

def _read_examples(db_path=DB_PATH):
    # Keep only the first completed run for each unique (seed, test id, policy)
    # to reduce duplicate weighting from repeated coverage checks or repeated runs.
    with _connect(db_path) as db:
        rows=db.execute('''SELECT c.seed,c.policy,c.difficulty,c.intensity,c.budget_min,r.test_id,r.features,r.result
            FROM training_rows r JOIN campaigns c ON c.key=r.campaign_key
            WHERE c.policy IN (?,?,?) AND r.result IN ('PASS','FAIL')
            ORDER BY c.stored_utc,c.key,r.step''',TRAIN_POLICIES).fetchall()
    out=[];seen=set()
    for seed,policy,difficulty,intensity,budget,test_id,features,result in rows:
        k=(seed,policy,difficulty,intensity,budget,test_id)
        if k in seen:continue
        seen.add(k)
        f=json.loads(features)
        if len(f)!=len(FEATURE_NAMES):raise ValueError('Data schema mismatch')
        out.append((int(seed),f,int(result=='FAIL')))
    return out

def _partition(seeds):
    # Immutable deterministic group split: no seed used on both sides.
    ordered=sorted(seeds,key=lambda s:hashlib.sha256(('satvv-learning-split-v1:'+str(s)).encode()).hexdigest())
    validation_n=max(2,round(.25*len(ordered)))
    return set(ordered[validation_n:]),set(ordered[:validation_n])

def train_candidate(db_path=DB_PATH,model_dir=MODEL_DIR,*,min_seeds=12,activate=True):
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import brier_score_loss, roc_auc_score
    from joblib import dump
    examples=_read_examples(db_path)
    seeds={v[0] for v in examples}
    if len(seeds)<min_seeds:
        raise ValueError(f'Need >= {min_seeds} distinct eligible seeds; found {len(seeds)}. Collect more independent campaigns first.')
    train_seeds,val_seeds=_partition(seeds)
    training=[x for x in examples if x[0] in train_seeds]
    validation=[x for x in examples if x[0] in val_seeds]
    x=np.asarray([x[1] for x in training],dtype=float)
    y=np.asarray([x[2] for x in training],dtype=int)
    xv=np.asarray([x[1] for x in validation],dtype=float)
    yv=np.asarray([x[2] for x in validation],dtype=int)
    if len(set(y))<2 or sum(y)<4 or (len(y)-sum(y))<4:
        raise ValueError('Need at least four PASS and four FAIL examples in training seeds. Collect more diverse scenarios.')
    if len(set(yv))<2:
        raise ValueError('Validation split must contain PASS and FAIL examples; collect more diverse seeds.')
    model=RandomForestClassifier(n_estimators=120,max_depth=9,min_samples_leaf=3,
                                  random_state=11012026,n_jobs=1,class_weight='balanced_subsample')
    model.fit(x,y)
    scores=model.predict_proba(xv)[:,list(model.classes_).index(1)]
    baseline=float(y.mean()); brier=float(brier_score_loss(yv,scores));base=float(brier_score_loss(yv,np.full(len(yv),baseline)))
    auc=float(roc_auc_score(yv,scores))
    # AUC against ranking and Brier against a constant predictor; no automatic
    # claim that next-test ordering is better before a separate paired evaluation.
    valid=bool(brier<base and auc>=.5)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    ident=stamp+'_'+uuid4().hex[:8]
    dest=Path(model_dir);dest.mkdir(parents=True,exist_ok=True)
    filename=f'ranker_{ident}.joblib'
    model_path=dest/filename
    dump(model,model_path)
    sha=hashlib.sha256(model_path.read_bytes()).hexdigest()
    meta={'id':ident,'created_utc':datetime.now(timezone.utc).isoformat(),
          'feature_names':list(FEATURE_NAMES),'model_file':filename,'sha256':sha,
          'train_seeds':sorted(train_seeds),'validation_seeds':sorted(val_seeds),
          'all_seen_seeds':sorted(seeds),'train_rows':len(training),'validation_rows':len(validation),
          'train_fail_rows':int(sum(y)),'validation_fail_rows':int(sum(yv)),
          'validation_auc':round(auc,5),'validation_brier':round(brier,5),
          'constant_baseline_brier':round(base,5), 'validation_pass':valid,
          'training_policies':list(TRAIN_POLICIES),'training_source':'logged synthetic executed PASS/FAIL tests only',
          'limits':'Same-generator synthetic validation. Correlated trajectories, selection bias and domain shift remain.'}
    (dest/f'ranker_{ident}.json').write_text(json.dumps(meta,indent=2)+'\n')
    if activate and valid:
        (dest/'active.json').write_text(json.dumps({'model_id':ident,'metadata_file':f'ranker_{ident}.json'},indent=2)+'\n')
        meta['activated']=True
    else:meta['activated']=False
    return meta

def load_active(model_dir=MODEL_DIR):
    from joblib import load
    d=Path(model_dir)
    active=d/'active.json'
    if not active.exists():return None,None
    pointer=json.loads(active.read_text())
    ident=pointer['model_id']
    if not ident.replace('_','').isalnum() or pointer['metadata_file']!=f'ranker_{ident}.json':
        raise ValueError('Invalid local model pointer')
    metadata=json.loads((d/pointer['metadata_file']).read_text())
    if metadata['id']!=ident or metadata['feature_names']!=list(FEATURE_NAMES):
        raise ValueError('Incompatible active learning model')
    filename=f'ranker_{ident}.joblib'
    path=d/filename
    if filename!=metadata['model_file'] or hashlib.sha256(path.read_bytes()).hexdigest()!=metadata['sha256']:
        raise ValueError('Model checksum mismatch; refusing to load')
    # joblib is pickle-based. Only load models locally created by this app.
    return load(path),metadata

def learning_status(db_path=DB_PATH,model_dir=MODEL_DIR):
    status=database_status(db_path)
    try:
        model,meta=load_active(model_dir)
        status['active_model']=None if model is None else {
            k:meta[k] for k in ('id','created_utc','train_rows','validation_rows','validation_auc',
             'validation_brier','constant_baseline_brier','all_seen_seeds','validation_pass')}
    except Exception as exc:
        status['active_model_error']=str(exc);status['active_model']=None
    return status

def check_independent_seeds(seeds, metadata):
    overlapping=set(seeds).intersection(metadata['all_seen_seeds'])
    if overlapping:raise ValueError('Independent evaluation overlaps model-development seeds: '+', '.join(map(str,sorted(overlapping)))+
        '. Use entirely new seed numbers.')
    return True
