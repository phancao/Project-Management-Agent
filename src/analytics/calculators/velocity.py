"""
Velocity chart calculator.

Shows team velocity over multiple sprints (committed vs completed).
"""

from typing import List, Dict, Any
import statistics

from src.analytics.models import (
    ChartResponse, ChartSeries, ChartDataPoint, ChartType,
    SprintData, VelocityDataPoint
)


class VelocityCalculator:
    """Calculates velocity chart data"""
    
    @staticmethod
    def calculate(sprint_history: List[SprintData]) -> ChartResponse:
        """
        Calculate velocity chart from sprint history.
        
        Args:
            sprint_history: List of completed sprints with work items
        
        Returns:
            ChartResponse with committed and completed velocity series
        """
        
        if not sprint_history:
            return ChartResponse(
                chart_type=ChartType.VELOCITY,
                title="Team Velocity",
                series=[],
                metadata={"error": "No sprint data available"}
            )
        
        # Extract velocity data from sprints
        velocity_data = []
        for i, sprint in enumerate(sprint_history, start=1):
            planned = sprint.planned_points or 0
            completed = sprint.completed_points or 0
            
            velocity_data.append(VelocityDataPoint(
                sprint_name=sprint.name,
                sprint_number=i,
                committed=planned,
                completed=completed,
                carry_over=0  # TODO: Calculate from previous sprint
            ))
        
        return VelocityCalculator.calculate_from_data(velocity_data)
    
    @staticmethod
    def calculate_from_data(velocity_data: List[VelocityDataPoint]) -> ChartResponse:
        """
        Calculate velocity chart from velocity data points.
        
        Args:
            velocity_data: List of velocity data points
        
        Returns:
            ChartResponse with committed and completed velocity series
        """
        
        if not velocity_data:
            return ChartResponse(
                chart_type=ChartType.VELOCITY,
                title="Team Velocity",
                series=[],
                metadata={"error": "No velocity data available"}
            )
        
        # Build series
        committed_series = ChartSeries(
            name="Committed",
            data=[
                ChartDataPoint(
                    label=vd.sprint_name,
                    value=round(vd.committed, 1),
                    metadata={"sprint_number": vd.sprint_number}
                )
                for vd in velocity_data
            ],
            color="#94a3b8",  # Gray
            type="bar"
        )
        
        completed_series = ChartSeries(
            name="Completed",
            data=[
                ChartDataPoint(
                    label=vd.sprint_name,
                    value=round(vd.completed, 1),
                    metadata={"sprint_number": vd.sprint_number}
                )
                for vd in velocity_data
            ],
            color="#10b981",  # Green
            type="bar"
        )
        
        # Calculate statistics
        completed_values = [vd.completed for vd in velocity_data]
        committed_values = [vd.committed for vd in velocity_data]
        
        avg_velocity = statistics.mean(completed_values) if completed_values else 0
        median_velocity = statistics.median(completed_values) if completed_values else 0
        
        # Calculate trend (simple linear regression slope)
        trend = VelocityCalculator._calculate_trend(completed_values)
        
        # Calculate predictability (how close completed is to committed)
        predictability_scores = []
        for vd in velocity_data:
            if vd.committed > 0:
                score = min(vd.completed / vd.committed, 1.0)
                predictability_scores.append(score)
        
        avg_predictability = statistics.mean(predictability_scores) if predictability_scores else 0
        
        # Calculate completion rates for each sprint
        completion_rates = [
            round((vd.completed / vd.committed * 100), 1) if vd.committed > 0 else 0
            for vd in velocity_data
        ]
        
        return ChartResponse(
            chart_type=ChartType.VELOCITY,
            title=f"Team Velocity (Last {len(velocity_data)} Sprints)",
            series=[committed_series, completed_series],
            metadata={
                "average_velocity": round(avg_velocity, 1),
                "median_velocity": round(median_velocity, 1),
                "trend": trend,
                "predictability_score": round(avg_predictability, 2),
                "sprint_count": len(velocity_data),
                "completion_rates": completion_rates,
                "latest_velocity": round(completed_values[-1], 1) if completed_values else 0,
                "velocity_range": {
                    "min": round(min(completed_values), 1) if completed_values else 0,
                    "max": round(max(completed_values), 1) if completed_values else 0
                }
            }
        )
    
    @staticmethod
    def _calculate_trend(values: List[float]) -> str:
        """
        Calculate trend direction from a list of values.
        
        Returns:
            "increasing", "decreasing", or "stable"
        """
        if len(values) < 2:
            return "stable"
        
        # Simple linear regression slope
        n = len(values)
        x = list(range(n))
        
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        # Consider trend significant if slope is > 5% of mean
        threshold = y_mean * 0.05
        
        if slope > threshold:
            return "increasing"
        elif slope < -threshold:
            return "decreasing"
        else:
            return "stable"

















