import json
from scripts.convert_charity import FIELDS,write_csv
from scripts.evaluate_charity import run,fast_score,features,counts,metrics
from src.matching import Record,score


def test_evaluation_and_frozen_input(tmp_path):
    companies=[dict(id=str(i).zfill(8),name=f'Charity {i} Ltd',address=f'{i} Main Road',postcode=f'TN{i+1} 1AB') for i in range(10)]
    queries=[dict(c,id=f'charity:{i}',name=f'Charity {i}') for i,c in enumerate(companies)]
    truth=[dict(charity_id=q['id'],company_number=c['id']) for q,c in zip(queries,companies)]
    write_csv(tmp_path/'charities.csv',FIELDS,queries)
    write_csv(tmp_path/'companies.csv',FIELDS,companies)
    write_csv(tmp_path/'truth.csv',['charity_id','company_number'],truth)
    a,b=Record(**queries[0]),Record(**companies[0])
    assert fast_score(features(a),features(b))==score(a,b)
    assert metrics([counts(set(),'missing',{'other'})])['recall']==0
    run(tmp_path,'tune'); run(tmp_path,'holdout')
    result=json.loads((tmp_path/'evaluation.json').read_text())
    assert result['heldout_queries']==4
    assert result['tuned_offline']['recall']==1
    assert result['blocking']['blocking_recall_all']==1
