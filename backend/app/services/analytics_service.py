from collections import Counter
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.scan import Alert, ScanResult
from app.models.supply_chain import SupplyChain
from app.schemas.analytics import (
    ChainAnalytics,
    GlobalAnalytics,
    RegionStat,
    ScanHistoryEntry,
    ScanStatusBreakdown,
    SeverityBreakdown,
)

TOP_REGIONS_LIMIT = 5
SCAN_HISTORY_LIMIT = 20


def _severity_breakdown(alerts: list[Alert]) -> SeverityBreakdown:
    counts = Counter(a.severity for a in alerts)
    return SeverityBreakdown(
        critical=counts.get("critical", 0),
        high=counts.get("high", 0),
        medium=counts.get("medium", 0),
        low=counts.get("low", 0),
    )


def _top_regions(alerts: list[Alert]) -> list[RegionStat]:
    counts = Counter(a.region for a in alerts)
    return [
        RegionStat(region=r, count=c)
        for r, c in counts.most_common(TOP_REGIONS_LIMIT)
    ]


def get_global_analytics(db: Session, user_id: UUID) -> GlobalAnalytics:
    chains = db.query(SupplyChain).filter(SupplyChain.owner_id == user_id).all()
    chain_ids = [c.id for c in chains]

    if not chain_ids:
        return GlobalAnalytics(
            total_alerts=0,
            severity_breakdown=SeverityBreakdown(),
            scan_status_breakdown=ScanStatusBreakdown(),
            top_regions=[],
            total_supply_chains=0,
        )

    alerts = (
        db.query(Alert)
        .filter(Alert.supply_chain_id.in_(chain_ids))
        .all()
    )

    scans = (
        db.query(ScanResult)
        .filter(ScanResult.supply_chain_id.in_(chain_ids))
        .all()
    )

    status_counts = Counter(s.status for s in scans)

    return GlobalAnalytics(
        total_alerts=len(alerts),
        severity_breakdown=_severity_breakdown(alerts),
        scan_status_breakdown=ScanStatusBreakdown(
            completed=status_counts.get("completed", 0),
            failed=status_counts.get("failed", 0),
            running=status_counts.get("running", 0),
            pending=status_counts.get("pending", 0),
        ),
        top_regions=_top_regions(alerts),
        total_supply_chains=len(chains),
    )


def get_chain_analytics(db: Session, supply_chain_id: UUID) -> ChainAnalytics:
    alerts = (
        db.query(Alert)
        .filter(Alert.supply_chain_id == supply_chain_id)
        .all()
    )

    scans = (
        db.query(ScanResult)
        .filter(ScanResult.supply_chain_id == supply_chain_id)
        .order_by(ScanResult.created_at.desc())
        .limit(SCAN_HISTORY_LIMIT)
        .all()
    )

    # Count alerts per scan for the history list.
    alert_counts_by_scan: Counter = Counter(
        a.scan_result_id for a in alerts
    )

    scan_history = [
        ScanHistoryEntry(
            scan_id=str(s.id),
            status=s.status,
            started_at=s.started_at.isoformat() if s.started_at else None,
            completed_at=s.completed_at.isoformat() if s.completed_at else None,
            alert_count=alert_counts_by_scan.get(s.id, 0),
            timing=s.timing,
        )
        for s in scans
    ]

    return ChainAnalytics(
        total_alerts=len(alerts),
        severity_breakdown=_severity_breakdown(alerts),
        top_regions=_top_regions(alerts),
        scan_history=scan_history,
    )