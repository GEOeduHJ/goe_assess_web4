"""채점 결과의 Excel 파일 및 기타 내보내기 형식 생성 서비스."""
from __future__ import annotations

import logging
import os
import statistics
import tempfile
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
from openpyxl.utils import get_column_letter

from models.result_model import GradingResult


class ExportService:
    """채점 결과를 다양한 형식으로 내보내는 서비스."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def create_results_excel(self, results: List[GradingResult]) -> str:
        if not results:
            raise ValueError("채점 결과가 없어 Excel 파일을 생성할 수 없습니다.")

        self._ensure_relative_grades(results)
        self._validate_results(results)

        temp_dir = tempfile.gettempdir()
        if not os.access(temp_dir, os.W_OK):
            raise PermissionError(f"임시 디렉토리에 쓰기 권한이 없습니다: {temp_dir}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = os.path.join(temp_dir, f"grading_results_{timestamp}.xlsx")
        self.logger.info("Excel 파일 생성 시작: %s", excel_path)

        try:
            with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                self._create_main_results_sheet(results, writer)
                self._create_element_scores_sheet(results, writer)
                self._create_summary_sheet(results, writer)
                self._create_feedback_sheet(results, writer)
        except Exception as exc:
            raise Exception(f"Excel 파일 작성 중 오류가 발생했습니다: {exc}") from exc

        if not os.path.exists(excel_path) or os.path.getsize(excel_path) == 0:
            raise Exception("Excel 파일이 생성되지 않았거나 비어있습니다.")

        self.logger.info("Excel 파일 생성 완료: %s", excel_path)
        return excel_path

    def _validate_results(self, results: List[GradingResult]) -> None:
        for index, result in enumerate(results, 1):
            if not isinstance(result, GradingResult):
                raise ValueError(f"결과 {index}번이 올바른 GradingResult 형식이 아닙니다.")
            if not result.student_name.strip():
                raise ValueError(f"결과 {index}번의 학생명이 비어있습니다.")
            for element in result.element_scores:
                _ = element.element_name
                _ = element.score
                _ = element.max_score
                _ = element.percentage

    def _create_main_results_sheet(self, results: List[GradingResult], writer: pd.ExcelWriter) -> None:
        main_data = []
        for result in results:
            row = {
                "학생명": result.student_name,
                "반": result.student_class_number,
                "상태": getattr(result, "status", "success"),
                "오류메시지": getattr(result, "error_message", ""),
                "원본답안": result.original_answer or "[답안 없음]",
                "총점": result.total_score,
                "만점": result.total_max_score,
                "백분율": round(result.percentage, 1),
                "등급": result.get_relative_grade(),
                "채점시간(초)": round(result.grading_time_seconds, 1),
                "채점완료시각": result.graded_at.strftime("%Y-%m-%d %H:%M:%S") if result.graded_at else "",
                "전체피드백": result.overall_feedback or "[피드백 없음]",
            }
            for element in result.element_scores:
                row[f"{element.element_name}_점수"] = element.score
                row[f"{element.element_name}_만점"] = element.max_score
                row[f"{element.element_name}_백분율"] = round(element.percentage, 1)
                row[f"{element.element_name}_판단근거"] = element.reasoning or "[판단근거 없음]"
                row[f"{element.element_name}_피드백"] = element.feedback or "[피드백 없음]"
            main_data.append(row)

        df_main = pd.DataFrame(main_data)
        df_main.to_excel(writer, sheet_name="채점결과", index=False)
        self._auto_fit_columns(writer.sheets["채점결과"], df_main)

    def _create_element_scores_sheet(self, results: List[GradingResult], writer: pd.ExcelWriter) -> None:
        element_data = []
        for result in results:
            for element in result.element_scores:
                element_data.append(
                    {
                        "학생명": result.student_name,
                        "반": result.student_class_number,
                        "상태": getattr(result, "status", "success"),
                        "원본답안": result.original_answer or "[답안 없음]",
                        "평가요소": element.element_name,
                        "획득점수": element.score,
                        "만점": element.max_score,
                        "백분율": round(element.percentage, 1),
                        "판단근거": element.reasoning or "[판단근거 없음]",
                        "요소별피드백": element.feedback or "[피드백 없음]",
                        "채점시간(초)": round(result.grading_time_seconds, 1),
                    }
                )

        if not element_data:
            self.logger.warning("평가요소별 상세 데이터가 없어 해당 시트를 생성하지 않습니다.")
            return

        df_elements = pd.DataFrame(element_data)
        df_elements.to_excel(writer, sheet_name="평가요소별상세", index=False)
        self._auto_fit_columns(writer.sheets["평가요소별상세"], df_elements)

    def _create_summary_sheet(self, results: List[GradingResult], writer: pd.ExcelWriter) -> None:
        percentages = [result.percentage for result in results]
        grading_times = [result.grading_time_seconds for result in results]
        successful = [result for result in results if getattr(result, "status", "success") == "success"]
        failed = [result for result in results if getattr(result, "status", "success") == "failed"]

        summary_data = [
            ["전체 통계", ""],
            ["총 학생 수", len(results)],
            ["성공 결과 수", len(successful)],
            ["실패 결과 수", len(failed)],
            ["평균 점수 (%)", round(statistics.mean(percentages), 1) if percentages else 0],
            ["중앙값 (%)", round(statistics.median(percentages), 1) if percentages else 0],
            ["표준편차", round(statistics.stdev(percentages), 1) if len(percentages) > 1 else 0],
            ["평균 채점시간 (초)", round(statistics.mean(grading_times), 1) if grading_times else 0],
            ["총 채점시간 (초)", round(sum(grading_times), 1)],
            ["", ""],
            ["등급 분포", "학생 수"],
        ]

        grade_counts: Dict[str, int] = {}
        for result in results:
            grade = result.get_relative_grade()
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        for grade in ["1", "2", "3", "4", "5"]:
            count = grade_counts.get(grade, 0)
            percentage = (count / len(results) * 100) if results else 0
            summary_data.append([f"{grade}등급", f"{count}명 ({percentage:.1f}%)"])

        if results and results[0].element_scores:
            summary_data.extend([["", ""], ["평가요소별 통계", "평균 점수 (%)"]])
            element_data: Dict[str, List[float]] = {}
            for result in results:
                for element in result.element_scores:
                    element_data.setdefault(element.element_name, []).append(element.percentage)
            for element_name, values in element_data.items():
                summary_data.append([element_name, round(statistics.mean(values), 1)])

        df_summary = pd.DataFrame(summary_data, columns=["항목", "값"])
        df_summary.to_excel(writer, sheet_name="요약통계", index=False)
        self._auto_fit_columns(writer.sheets["요약통계"], df_summary)

    def _create_feedback_sheet(self, results: List[GradingResult], writer: pd.ExcelWriter) -> None:
        feedback_data = []
        for result in results:
            if result.overall_feedback and result.overall_feedback.strip():
                feedback_data.append(
                    {
                        "학생명": result.student_name,
                        "반": result.student_class_number,
                        "상태": getattr(result, "status", "success"),
                        "원본답안": result.original_answer or "[답안 없음]",
                        "피드백유형": "전체피드백",
                        "평가요소": "전체",
                        "피드백내용": result.overall_feedback,
                        "점수": f"{result.total_score}/{result.total_max_score}",
                        "백분율": round(result.percentage, 1),
                    }
                )
            for element in result.element_scores:
                if element.feedback and element.feedback.strip():
                    feedback_data.append(
                        {
                            "학생명": result.student_name,
                            "반": result.student_class_number,
                            "상태": getattr(result, "status", "success"),
                            "원본답안": result.original_answer or "[답안 없음]",
                            "피드백유형": "요소별피드백",
                            "평가요소": element.element_name,
                            "피드백내용": element.feedback,
                            "점수": f"{element.score}/{element.max_score}",
                            "백분율": round(element.percentage, 1),
                        }
                    )

        if not feedback_data:
            self.logger.warning("피드백 데이터가 없어 상세피드백 시트를 생성하지 않습니다.")
            return

        df_feedback = pd.DataFrame(feedback_data)
        df_feedback.to_excel(writer, sheet_name="상세피드백", index=False)
        self._auto_fit_columns(writer.sheets["상세피드백"], df_feedback, max_width=70)

    def format_results_for_export(self, results: List[GradingResult]) -> Dict[str, Any]:
        if not results:
            return {}

        self._ensure_relative_grades(results)
        percentages = [result.percentage for result in results]
        times = [result.grading_time_seconds for result in results]
        summary_stats = {
            "total_students": len(results),
            "success_count": sum(1 for result in results if getattr(result, "status", "success") == "success"),
            "failed_count": sum(1 for result in results if getattr(result, "status", "success") == "failed"),
            "average_score": statistics.mean(percentages),
            "median_score": statistics.median(percentages),
            "std_deviation": statistics.stdev(percentages) if len(percentages) > 1 else 0,
            "min_score": min(percentages),
            "max_score": max(percentages),
            "average_time": statistics.mean(times),
            "total_time": sum(times),
        }

        grade_distribution: Dict[str, int] = {}
        for result in results:
            grade = result.get_relative_grade()
            grade_distribution[grade] = grade_distribution.get(grade, 0) + 1

        element_performance: Dict[str, Any] = {}
        if results[0].element_scores:
            raw_element_values: Dict[str, List[float]] = {}
            for result in results:
                for element in result.element_scores:
                    raw_element_values.setdefault(element.element_name, []).append(element.percentage)
            for element_name, values in raw_element_values.items():
                element_performance[element_name] = {
                    "average": statistics.mean(values),
                    "median": statistics.median(values),
                    "std_deviation": statistics.stdev(values) if len(values) > 1 else 0,
                    "min": min(values),
                    "max": max(values),
                }

        student_details = []
        for result in results:
            student_details.append(
                {
                    "name": result.student_name,
                    "class_number": result.student_class_number,
                    "status": getattr(result, "status", "success"),
                    "error_message": getattr(result, "error_message", ""),
                    "original_answer": result.original_answer,
                    "total_score": result.total_score,
                    "total_max_score": result.total_max_score,
                    "percentage": result.percentage,
                    "grade": result.get_relative_grade(),
                    "grading_time": result.grading_time_seconds,
                    "graded_at": result.graded_at.isoformat() if result.graded_at else None,
                    "overall_feedback": result.overall_feedback,
                    "element_scores": [
                        {
                            "element_name": element.element_name,
                            "score": element.score,
                            "max_score": element.max_score,
                            "percentage": element.percentage,
                            "feedback": element.feedback,
                            "reasoning": element.reasoning,
                        }
                        for element in result.element_scores
                    ],
                }
            )

        return {
            "summary_statistics": summary_stats,
            "grade_distribution": grade_distribution,
            "element_performance": element_performance,
            "student_details": student_details,
            "export_timestamp": datetime.now().isoformat(),
        }

    def generate_download_link(self, file_path: str) -> str:
        return file_path

    def _ensure_relative_grades(self, results: List[GradingResult]) -> None:
        grade_mapping = GradingResult.calculate_relative_grades(results)
        for result in results:
            key = f"{result.student_name}_{result.student_class_number}"
            if key in grade_mapping:
                result.set_relative_grade(grade_mapping[key])

    def _auto_fit_columns(self, worksheet, dataframe: pd.DataFrame, max_width: int = 50) -> None:
        for column_index, column_name in enumerate(dataframe.columns, 1):
            try:
                column_length = max(dataframe[column_name].astype(str).map(len).max(), len(str(column_name)))
                worksheet.column_dimensions[get_column_letter(column_index)].width = min(column_length + 2, max_width)
            except Exception as exc:
                self.logger.warning("열 너비 조정 실패 (%s): %s", column_name, exc)


def create_export_service() -> ExportService:
    return ExportService()
