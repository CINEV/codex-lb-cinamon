from __future__ import annotations

from pathlib import Path

import yaml


def test_chart_kube_version_floor_is_1_32() -> None:
    chart = yaml.safe_load(Path("deploy/helm/codex-lb/Chart.yaml").read_text(encoding="utf-8"))
    assert chart["kubeVersion"] == ">=1.32.0-0"


def test_chart_readme_documents_fork_support_policy() -> None:
    readme = Path("deploy/helm/codex-lb/README.md").read_text(encoding="utf-8")
    assert "Helm/Kubernetes 배포 문서는 더 이상 적극적으로 관리하지 않습니다." in readme
    assert "차트 메타데이터의 최소 Kubernetes 버전은 `1.32`입니다." in readme
    assert "CI의 차트 검증은 `1.35` 렌더링 기준을 사용합니다." in readme


def test_ci_uses_1_32_minimum_and_1_35_baseline() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "make helm-check" in workflow
    assert "HELM_SMOKE_BUILD_IMAGE=false helm-smoke-kind" in workflow
    assert "set -e -o pipefail" in makefile
    assert "for version in 1.32.0 1.35.0" in makefile
    assert '-kubernetes-version "$${version}"' in makefile
    assert "kind create cluster --name codex-lb-smoke --image kindest/node:v1.35.0 --wait 120s" in makefile
    assert "kubeconform (K8s 1.25.0)" not in workflow
    assert "kubeconform (K8s 1.28.0)" not in workflow
    assert "kubeconform (K8s 1.31.0)" not in workflow
