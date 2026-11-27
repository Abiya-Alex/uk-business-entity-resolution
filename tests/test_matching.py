import pytest
from src.matching import Record, CandidateIndex, score, decision, name_key, postcode_key
from src.evaluate import evaluate


def rec(id='1',name='ABC Foods Ltd',address='25 High St.',postcode='TN9 1AB'):
    return Record(id=id,name=name,address=address,postcode=postcode)


def test_normalize():
    assert name_key('ABC Foods LIMITED.')=='abc foods'
    assert postcode_key('tn9 1ab')=='TN91AB'


def test_score():
    assert score(rec(),rec('2','ABC Foods Limited','25 High Street'))==100
    assert score(rec(),rec('3','XYZ','Elsewhere','AB1 2CD'))<65
    assert score(rec(address='',postcode=''),rec(address='',postcode=''))==55

@pytest.mark.parametrize('value,expected',[(90,'auto_match'),(89.99,'review'),(65,'review'),(64.99,'no_match')])
def test_decision(value,expected):
    assert decision(value)==expected


def test_index():
    idx=CandidateIndex([rec(),rec('2','XYZ','Elsewhere','AB1 2CD')])
    assert [r.id for r in idx.candidates(rec('3'))]==['1']


def test_evaluate():
    row=dict(a_name='ABC Foods Ltd',a_address='25 High St',a_postcode='TN9 1AB',b_name='ABC Foods Limited',b_address='25 High Street',b_postcode='TN9 1AB',label='1')
    assert evaluate([row])['f1']==1
