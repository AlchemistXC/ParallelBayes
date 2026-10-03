import argparse
import json
from pathlib import Path
from .experiment import write_json,run_protocol,recover_lock
from .sampling import environment


def main():
    parser=argparse.ArgumentParser(description='ParallelBayes frozen experiment runner')
    commands=parser.add_subparsers(dest='command',required=True)
    env=commands.add_parser('environment'); env.add_argument('--output',default='execution/environment.json')
    run=commands.add_parser('run'); run.add_argument('protocol'); run.add_argument('--output',required=True)
    run.add_argument('--root',default='.'); run.add_argument('--platform',choices=['cpu','gpu'],default='cpu')
    run.add_argument('--retry-failed',action='store_true'); run.add_argument('--limit',type=int)
    recover=commands.add_parser('recover'); recover.add_argument('output')
    args=parser.parse_args()
    if args.command=='environment': write_json(args.output,environment())
    elif args.command=='recover': recover_lock(args.output)
    else: run_protocol(args.protocol,args.output,args.root,args.platform,args.retry_failed,args.limit)

if __name__=='__main__': main()
