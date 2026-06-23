from pydantic import BaseModel


class SeverityBreakdown(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class ScanStatusBreakdown(BaseModel):
    completed: int = 0
    failed: int = 0
    running: int = 0
    pending: int = 0


class RegionStat(BaseModel):
    region: str
    count: int


class ScanHistoryEntry(BaseModel):
    scan_id: str
    status: str
    started_at: str | None
    completed_at: str | None
    alert_count: int
    timing: dict | None


class GlobalAnalytics(BaseModel):
    total_alerts: int
    severity_breakdown: SeverityBreakdown
    scan_status_breakdown: ScanStatusBreakdown
    top_regions: list[RegionStat]
    total_supply_chains: int


class ChainAnalytics(BaseModel):
    total_alerts: int
    severity_breakdown: SeverityBreakdown
    top_regions: list[RegionStat]
    scan_history: list[ScanHistoryEntry]


class ExecutiveSummary(BaseModel):
    summary: str
    cached: bool