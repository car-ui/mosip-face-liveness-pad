from scripts.evaluate_dataset import summarize


def test_pad_error_denominators_do_not_hide_nonresponses():
    rows = [{'label':'attack','accepted':True}, {'label':'attack','accepted':False},
            {'label':'attack','accepted':None}, {'label':'bona_fide','accepted':False},
            {'label':'bona_fide','accepted':None}]
    report = summarize(rows)
    assert report['APCER'] == .5
    assert report['BPCER'] == 1
    assert report['attack']['nonResponses'] == 1
    assert report['bona_fide']['nonResponses'] == 1
    assert summarize([])['APCER'] is None
