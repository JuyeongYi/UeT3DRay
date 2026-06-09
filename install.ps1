#!/usr/bin/env pwsh
#Requires -Version 7.0
<#
.SYNOPSIS
  T3DGraphViewer(t3dgraph[gui])를 krafton 깃 저장소에서 직접 설치한다.
.DESCRIPTION
  uv tool install 로 git+ssh URL에서 GUI 의존성(PySide6)을 포함해 설치한다.
  재실행 시 --force 로 최신 커밋 기준으로 갱신한다.
.NOTES
  사전 요구: uv(https://docs.astral.sh/uv/), github.krafton.com SSH 키/접근 권한.
#>

$ErrorActionPreference = 'Stop'

# scp형 주소(git@host:path)는 pip/uv가 인식하지 못하므로 git+ssh URL 스킴으로 변환해 사용한다.
$PackageSpec = 't3dgraph[gui] @ git+ssh://git@github.krafton.com/Visual-R-D/T3DGraphViewer.git'

$UvCommand = Get-Command uv -ErrorAction SilentlyContinue
if (-not $UvCommand) {
    Write-Error 'uv를 찾을 수 없습니다. https://docs.astral.sh/uv/ 에서 먼저 설치하세요.'
    exit 1
}

Write-Host 'T3DGraphViewer 설치 중 (t3dgraph[gui])...' -ForegroundColor Cyan
Write-Host "  소스: $PackageSpec"

uv tool install --force $PackageSpec
if ($LASTEXITCODE -ne 0) {
    Write-Error "설치 실패 (uv 종료 코드 $LASTEXITCODE). SSH 키/접근 권한을 확인하세요."
    exit $LASTEXITCODE
}

Write-Host '설치 완료.' -ForegroundColor Green
Write-Host '  GUI 실행: t3dgraph-gui'
Write-Host '  CLI 실행: t3dgraph'
