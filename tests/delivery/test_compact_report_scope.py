"""Presentation-only scope checks; no scientific arrays, R, sampler or intervals."""
from pathlib import Path
import sys

sys.path[:0]=[str(Path(__file__).resolve().parents[2]/'scripts/analysis')]
from formal_report_text import write_report


def receipt(scope):
    return dict(fixture=False,frame=dict(scope=scope,execution_contract='windows-compact-contract-v1'),
        statistics_manifest_sha256='0'*64,source_models=[],
        figures=[dict(model='G1',kind='execution_costs',file='costs.pdf',source_table='costs.json')])


def test_formal_compact_cache_caption_does_not_claim_bca_interval(tmp_path):
    write_report(tmp_path,receipt('formal_inference'))
    md=(tmp_path/'report.md').read_text(encoding='utf-8')
    caption=md.split('### G1 / execution costs')[1].split('来源：')[0]
    assert '缓存' in caption and '不生成区间' in caption
    assert '主任务' in caption and 'BCa' in caption


def test_compact_technical_report_does_not_claim_24_formal_repeats(tmp_path):
    write_report(tmp_path,receipt('technical_batch_validation'))
    md=(tmp_path/'report.md').read_text(encoding='utf-8')
    tex=(tmp_path/'report.tex').read_text(encoding='utf-8')
    assert '新正式研究为24次' not in md and '新24次完整四链重复' not in tex
    assert '正式重复数为0' in md and '正式重复数为0' in tex
    caption=md.split('### G1 / execution costs')[1].split('来源：')[0]
    assert '技术' in caption and '不生成区间' in caption
