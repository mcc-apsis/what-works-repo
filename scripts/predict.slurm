#!/bin/bash

#SBATCH --time=06:00:00
#SBATCH --nodes=1
#SBATCH --mem=16G
#SBATCH --mail-user="maxca"
#SBATCH --output=data/logs/predict_%j.out
#SBATCH --error=data/logs/predict_%j.err
#SBATCH --chdir=/home/maxca/what-works-repo
#SBATCH --gres=gpu:1
#SBATCH --partition=gpu
#SBATCH --qos=gpumedium
#SBATCH --cpus-per-task=2
#SBATCH --mail-type=END,FAIL
#SBATCH --array=0-7

set -e
set -o xtrace

module load cuda

unset VIRTUAL_ENV
export PYTHONUNBUFFERED=1
export OPENBLAS_NUM_THREADS=1
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1
export UV_OFFLINE=1
export HF_HOME=/data/rd5/ecs/huggingface-cache
export UV_PROJECT_ENVIRONMENT=/home/maxca/software/WWCS/what-works-repo/.venv

JOB_ID=$SLURM_ARRAY_TASK_ID
NUM_JOBS=16

.venv/bin/python src/what_works_repo/classify/predict.py 1 --job-id=$JOB_ID --num-jobs=$NUM_JOBS