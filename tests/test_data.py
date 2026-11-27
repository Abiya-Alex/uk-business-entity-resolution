from src.convert import convert
from src.profile_data import profile


def test_conversion(tmp_path):
    source=tmp_path/'companies.csv'; target=tmp_path/'canonical.csv'
    source.write_text('CompanyNumber,CompanyName,RegAddress.PostCode,RegAddress.AddressLine1\n1,ABC Ltd,TN9 1AB,25 High Street\n2,Other,AB1 2CD,1 Road\n')
    assert convert(str(source),str(target),'companies',['TN'])==1
    assert profile(str(target))['records']==1


def test_fsa_conversion(tmp_path):
    source=tmp_path/'fsa.json'; target=tmp_path/'canonical.csv'
    source.write_text('{"establishments":[{"FHRSID":1,"BusinessName":"ABC","PostCode":"ME1 1AA"}]}')
    assert convert(str(source),str(target),'fsa',['ME'])==1
    assert profile(str(target))['missing']['address']==1


def test_sample_pairs(tmp_path, monkeypatch):
    from src.sample_pairs import main
    import sys
    source=tmp_path/'source.csv'; output=tmp_path/'pairs.csv'
    source.write_text('id,name,address,postcode\n1,ABC Ltd,25 High Street,TN9 1AB\n')
    monkeypatch.setattr(sys,'argv',['sample_pairs',str(source),str(source),str(output),'--count','1'])
    main()
    assert 'ABC Ltd' in output.read_text()
