"""Small project-owned axes alignment check, independent of authoring tools."""
import json,os,importlib.util
from pathlib import Path

def require_matplotlib_panel_alignment(fig,json_out,overlay_svg=None,tolerance_pt=1.5,gutter_tolerance_pt=1.5,strict=True):
    if os.environ.get("PB_ALIGNMENT_QA"):
        spec=importlib.util.spec_from_file_location("authoring_alignment",os.environ["PB_ALIGNMENT_QA"]);module=importlib.util.module_from_spec(spec)
        import sys
        sys.modules[spec.name]=module;spec.loader.exec_module(module)
        return module.require_matplotlib_panel_alignment(fig,json_out=json_out,overlay_svg=overlay_svg,tolerance_pt=tolerance_pt,gutter_tolerance_pt=gutter_tolerance_pt,strict=strict)
    boxes=[a.get_position().bounds for a in fig.axes];w,h=fig.get_size_inches()*72;violations=[]
    for i,b in enumerate(boxes):
        for j,c in enumerate(boxes[:i]):
            if abs((b[0]+b[2]/2)-(c[0]+c[2]/2))*w<tolerance_pt:
                if max(abs(b[0]-c[0]),abs(b[0]+b[2]-c[0]-c[2]))*w>tolerance_pt:violations.append([i,j,'column edges'])
            if abs((b[1]+b[3]/2)-(c[1]+c[3]/2))*h<tolerance_pt:
                if max(abs(b[1]-c[1]),abs(b[1]+b[3]-c[1]-c[3]))*h>tolerance_pt:violations.append([i,j,'row edges'])
    Path(json_out).write_text(json.dumps(dict(axes=boxes,violations=violations,scope='Axes row/column edges; text collisions require visual review'),indent=2))
    if strict and violations:raise ValueError(violations)
