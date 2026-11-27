import csv
from scripts.convert_charity import convert, company_number


def test_company_number_and_hidden_truth(tmp_path):
    assert company_number('123')=='00000123'
    assert company_number('SC123')=='SC000123'
    assert company_number('00000000')==''
    assert company_number('N/A')==''
    columns=['organisation_number','charity_name','charity_registration_status','charity_company_registration_number','charity_contact_postcode','date_of_extract']+[f'charity_contact_address{i}' for i in range(1,6)]
    source=tmp_path/'source.txt'
    with source.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns,delimiter='\t'); w.writeheader()
        for i,n,status in [(1,'123','Registered'),(2,'00000123','Registered'),(3,'456','Removed')]:
            w.writerow(dict(organisation_number=i,charity_name='Example Charity',charity_registration_status=status,charity_company_registration_number=n,charity_contact_postcode='TN9 1AB',date_of_extract='2026-11-27'))
    out=tmp_path/'out'; profile=convert(source,out,500)
    assert profile['registered_nonblank_company_number']==2
    assert profile['unique_eligible_companies']==1
    with (out/'charities.csv').open() as f: rows=list(csv.DictReader(f))
    with (out/'truth.csv').open() as f: truth=list(csv.DictReader(f))
    assert set(rows[0])=={'id','name','address','postcode'}
    assert rows[0]['id']==truth[0]['charity_id']
    assert truth[0]['company_number']=='00000123'
