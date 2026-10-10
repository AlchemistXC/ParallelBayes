"""Publication rendering preserves the saved scalar analysis and real zeros."""
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/analysis'),str(ROOT/'tests/handoff')]
from test_formal_report import make_bundle
from formal_report import build
from formal_publication_plots import configure,signed_axis,plt


def test_close_small_ticks_remain_distinct_and_zero_is_not_replaced():
    configure()
    fig,axes=plt.subplots(2,1)
    axes[0].plot([1,2],[2.25e-21,2.25e-21])
    info=signed_axis(axes[0],'y',[2.25e-21])
    axes[1].plot([1,2],[0.,0.])
    zero=signed_axis(axes[1],'y',[0.,0.])
    fig.canvas.draw()
    labels=[x.get_text() for x in axes[0].get_yticklabels()]
    assert len(labels)==len(set(labels))
    assert info['scale']==zero['scale']=='linear'
    assert not zero['zero_values_replaced']
    assert axes[1].lines[0].get_ydata().tolist()==[0.,0.]
    plt.close(fig)


def test_publication_layout_preserves_all_scalar_tables_and_missing_points(tmp_path):
    fitz=pytest.importorskip('fitz')
    source,digest=make_bundle(tmp_path/'source')
    old=tmp_path/'original';new=tmp_path/'publication'
    build(source,digest,old,fixture=True,render=False)
    result=build(source,digest,new,fixture=True,publication_layout=True)
    assert (old/'G1/tables.json').read_bytes()==(new/'G1/tables.json').read_bytes()
    assert result['new_sampler_calls']==result['new_statistical_repetitions']==0
    assert result['publication_layout'] and result['fixture']
    assert 'width=160mm' in (new/'report.tex').read_text()
    missing=json.loads((new/'G1/inference-2.contract.json').read_text())
    assert missing['points'] and all(not x['plotted'] for x in missing['points'])
    for figure in result['figures']:
        with fitz.open(new/figure['file']) as pdf:
            assert pdf[0].rect.width==pytest.approx(160/25.4*72,abs=.01)
            spans=[s for b in pdf[0].get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
            assert min(s['size'] for s in spans)>=8.49
            assert 'ARTIFICIAL TEST DATA' in pdf[0].get_text()
