"""Original-parameter function contract retained from the historical studies."""
from pathlib import Path
import sys,math
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))


def test_original_gaussian_and_logistic_estimands_keep_threshold_and_units():
    from inference_estimands import evaluate
    x=evaluate(dict(kind='gaussian',mean=[2.,-1.],covariance=[[4.,0.],[0.,1.]]),np.array([[[2.,-1.],[4.,0.],[6.,1.]]]))
    np.testing.assert_array_equal(x['values'],[[[0.,0.,0.],[1.,1.,0.],[2.,4.,1.]]])
    np.testing.assert_allclose(x['analytic_reference'],[0.,1.,.15865525393145707],atol=1e-15)
    y=evaluate(dict(kind='logistic'),np.array([[[math.log(3),-2.]]]))
    np.testing.assert_allclose(y['values'],[[[math.log(3),-2.,.75,1.]]],atol=1e-15)
    assert y['analytic_reference'] is None


def test_wells_keeps_rare_event_and_both_prediction_probabilities():
    from inference_estimands import evaluate
    x=evaluate(dict(kind='external_wells_distance'),np.array([[[math.log(3),math.log(2)]]]))
    assert x['names'][-3:]==['p_switch_0m','p_switch_100m','beta_positive']
    np.testing.assert_allclose(x['values'][0,0,-3:],[.75,6/7,1.],atol=1e-15)
    assert x['values'].shape==(1,1,7) and x['analytic_reference'] is None
