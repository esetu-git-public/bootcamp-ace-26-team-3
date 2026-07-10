"""
Unit tests for the Model Performance diagnostics router (model.py).
Tests get_model_metrics, deploy_model_version, and A/B test start/stop/status/results endpoints.

Author/Developer: Manthena Sri Harshitha
"""

import os
import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, mock_open, PropertyMock
from fastapi import HTTPException, BackgroundTasks
from backend.app.routers import model
from backend.app.schemas import ABTestConfig
from backend.app.core.model_service import ModelService


class TestModelPerformanceMetrics:
    """Tests for GET /model/metrics endpoint."""

    @pytest.mark.asyncio
    async def test_get_model_metrics_db_success(self):
        """Test successful metrics retrieval from the database."""
        mock_row = Mock()
        mock_row.model_version = "v1.3.0-custom"
        mock_row.accuracy = 0.8851
        mock_row.precision = 0.8624
        mock_row.recall = 0.8412
        mock_row.f1_score = 0.8517
        mock_row.roc_auc = 0.9125
        mock_row.confusion_matrix = '{"tp": 100, "fp": 10, "tn": 900, "fn": 15}'
        mock_row.feature_importance = '{"feature_1": 45.0, "feature_2": 25.0}'
        mock_row.evaluated_at = datetime(2026, 7, 10, 12, 0, 0)

        mock_db = Mock()
        mock_db.execute = Mock(return_value=Mock(fetchone=Mock(return_value=mock_row)))

        result = await model.get_model_metrics(db=mock_db, current_user="admin")

        assert result["model_version"] == "v1.3.0-custom"
        assert result["accuracy"] == 0.8851
        assert result["precision"] == 0.8624
        assert result["recall"] == 0.8412
        assert result["f1_score"] == 0.8517
        assert result["roc_auc"] == 0.9125
        assert result["confusion_matrix"] == {"tp": 100, "fp": 10, "tn": 900, "fn": 15}
        assert result["feature_importance"] == {"feature_1": 45.0, "feature_2": 25.0}
        assert result["evaluated_at"] == mock_row.evaluated_at

    @pytest.mark.asyncio
    async def test_get_model_metrics_db_fails_file_success(self, monkeypatch):
        """Test database failure falling back to a local JSON metrics file."""
        mock_db = Mock()
        mock_db.execute = Mock(side_effect=Exception("Database connection failure"))

        file_data = {
            "model_version": "v1.2.0-json",
            "accuracy": 0.85,
            "precision": 0.83,
            "recall": 0.81,
            "f1_score": 0.82,
            "roc_auc": 0.89,
            "confusion_matrix": {"tp": 120, "fp": 15, "tn": 1350, "fn": 10},
            "feature_importance": {"Tenure_Months": 34.2}
        }

        # Mock os.path.exists to true and patch the open call
        monkeypatch.setattr(os.path, "exists", lambda path: True)

        m = mock_open(read_data=json.dumps(file_data))
        with patch("builtins.open", m):
            result = await model.get_model_metrics(db=mock_db, current_user="admin")

        assert result["model_version"] == "v1.2.0-json"
        assert result["accuracy"] == 0.85
        assert result["confusion_matrix"]["tp"] == 120
        assert isinstance(result["evaluated_at"], datetime)

    @pytest.mark.asyncio
    async def test_get_model_metrics_all_fail(self, monkeypatch):
        """Test fallback to hardcoded mock metrics when both database and file access fail."""
        mock_db = Mock()
        mock_db.execute = Mock(side_effect=Exception("Database connection failure"))

        monkeypatch.setattr(os.path, "exists", lambda path: False)

        result = await model.get_model_metrics(db=mock_db, current_user="admin")

        assert result["model_version"] == "v1.2.0-catboost"
        assert result["accuracy"] == 0.8546
        assert result["precision"] == 0.8312
        assert result["confusion_matrix"]["tp"] == 1200
        assert isinstance(result["evaluated_at"], datetime)


class TestModelDeployment:
    """Tests for POST /model/deploy/{model_version} endpoint."""

    @pytest.mark.asyncio
    async def test_deploy_model_version_forbidden(self):
        """Verify non-admin users cannot deploy new model versions."""
        with pytest.raises(HTTPException) as exc_info:
            await model.deploy_model_version(
                model_version="v1.4.0",
                background_tasks=BackgroundTasks(),
                current_user={"username": "standard_user"}
            )
        assert exc_info.value.status_code == 403
        assert "Not authorized" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_deploy_model_version_success(self):
        """Verify admin user can deploy a model version, triggering background reload."""
        bg_tasks = Mock(spec=BackgroundTasks)

        with patch.object(model.model_service, "reload_model") as mock_reload:
            res = await model.deploy_model_version(
                model_version="v1.4.0",
                background_tasks=bg_tasks,
                current_user={"username": "admin"}
            )

            assert res["status"] == "IN_PROGRESS"
            assert res["model_version"] == "v1.4.0"
            bg_tasks.add_task.assert_called_once_with(model.model_service.reload_model, "v1.4.0")


class TestModelABTesting:
    """Tests for A/B testing endpoints."""

    @pytest.mark.asyncio
    async def test_start_ab_test_forbidden(self):
        """Verify non-admin users cannot start an A/B test."""
        config = ABTestConfig(challenger_version="v1.3.0", traffic_split_percent=20)
        with pytest.raises(HTTPException) as exc_info:
            await model.start_ab_test(config=config, current_user={"username": "standard_user"})
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_start_ab_test_champion_not_ready(self):
        """Verify A/B test cannot start if model service has no active champion loaded."""
        config = ABTestConfig(challenger_version="v1.3.0", traffic_split_percent=20)
        with patch.object(ModelService, "is_ready", new_callable=PropertyMock) as mock_ready:
            mock_ready.return_value = False
            with pytest.raises(HTTPException) as exc_info:
                await model.start_ab_test(config=config, current_user={"username": "admin"})
            assert exc_info.value.status_code == 503
            assert "Champion model not loaded" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_start_ab_test_same_version(self):
        """Verify challenger version cannot be the same as the champion version."""
        config = ABTestConfig(challenger_version="v1.2.0-catboost", traffic_split_percent=20)
        with patch.object(ModelService, "is_ready", new_callable=PropertyMock) as mock_ready, \
             patch.object(model.model_service, "champion_version", "v1.2.0-catboost"):
            mock_ready.return_value = True
            with pytest.raises(HTTPException) as exc_info:
                await model.start_ab_test(config=config, current_user={"username": "admin"})
            assert exc_info.value.status_code == 400
            assert "Challenger version cannot be the same" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_start_ab_test_challenger_not_found(self):
        """Verify starting A/B test raises 404 if challenger artifacts cannot be loaded."""
        config = ABTestConfig(challenger_version="v1.9.9", traffic_split_percent=20)
        with patch.object(ModelService, "is_ready", new_callable=PropertyMock) as mock_ready, \
             patch.object(model.model_service, "champion_version", "v1.2.0-catboost"), \
             patch.object(model.model_service, "models", {"v1.2.0-catboost": {}}), \
             patch.object(model.model_service, "load_artifacts") as mock_load:
            mock_ready.return_value = True

            with pytest.raises(HTTPException) as exc_info:
                await model.start_ab_test(config=config, current_user={"username": "admin"})
            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail
            mock_load.assert_called_once_with("v1.9.9", as_champion=False)

    @pytest.mark.asyncio
    async def test_start_ab_test_success(self):
        """Verify successful A/B test activation."""
        config = ABTestConfig(challenger_version="v1.3.0", traffic_split_percent=20)
        with patch.object(ModelService, "is_ready", new_callable=PropertyMock) as mock_ready, \
             patch.object(model.model_service, "champion_version", "v1.2.0-catboost"), \
             patch.object(model.model_service, "models", {"v1.2.0-catboost": {}, "v1.3.0": {}}), \
             patch.object(model.model_service, "get_ab_test_status") as mock_status:
            mock_ready.return_value = True
            mock_status.return_value = {"is_active": True, "challenger_version": "v1.3.0", "traffic_split_percent": 20}

            res = await model.start_ab_test(config=config, current_user={"username": "admin"})

            assert model.model_service.ab_test_config["is_active"] is True
            assert model.model_service.ab_test_config["challenger_version"] == "v1.3.0"
            assert model.model_service.ab_test_config["traffic_split_percent"] == 20
            assert res["is_active"] is True

    @pytest.mark.asyncio
    async def test_stop_ab_test_forbidden(self):
        """Verify non-admin users cannot stop an A/B test."""
        with pytest.raises(HTTPException) as exc_info:
            await model.stop_ab_test(current_user={"username": "standard_user"})
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_stop_ab_test_not_active(self):
        """Verify stopping A/B test fails with 400 if no A/B test is active."""
        with patch.dict(model.model_service.ab_test_config, {"is_active": False}):
            with pytest.raises(HTTPException) as exc_info:
                await model.stop_ab_test(current_user={"username": "admin"})
            assert exc_info.value.status_code == 400
            assert "No A/B test is currently active" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_stop_ab_test_success(self):
        """Verify successful deactivation of active A/B test."""
        with patch.dict(model.model_service.ab_test_config, {"is_active": True, "challenger_version": "v1.3.0", "traffic_split_percent": 20}), \
             patch.object(model.model_service, "get_ab_test_status") as mock_status:
            mock_status.return_value = {"is_active": False, "challenger_version": None, "traffic_split_percent": 0}

            res = await model.stop_ab_test(current_user={"username": "admin"})

            assert model.model_service.ab_test_config["is_active"] is False
            assert model.model_service.ab_test_config["challenger_version"] is None
            assert res["is_active"] is False

    @pytest.mark.asyncio
    async def test_get_ab_test_status(self):
        """Verify A/B test status reporting works."""
        with patch.object(model.model_service, "get_ab_test_status") as mock_status:
            mock_status.return_value = {"is_active": True, "challenger_version": "v1.3.0", "traffic_split_percent": 25}
            res = await model.get_ab_test_status(current_user={"username": "admin"})
            assert res["challenger_version"] == "v1.3.0"
            assert res["traffic_split_percent"] == 25

    @pytest.mark.asyncio
    async def test_get_ab_test_results_empty_versions(self):
        """Verify model comparison returns empty dictionary when no versions list is provided."""
        res = await model.get_ab_test_results(versions=[], db=Mock(), current_user={"username": "admin"})
        assert res == {"results": {}}

    @pytest.mark.asyncio
    async def test_get_ab_test_results_success(self):
        """Verify model comparison results query database and aggregate metrics correctly."""
        mock_row_1 = Mock()
        mock_row_1.model_version = "v1.2.0-catboost"
        mock_row_1.prediction_count = 100
        mock_row_1.average_churn_probability = 35.5
        mock_row_1.predicted_churn_count = 30
        mock_row_1.predicted_churn_rate = 30.0
        mock_row_1.high_risk_count = 20
        mock_row_1.medium_risk_count = 15
        mock_row_1.low_risk_count = 65

        mock_row_2 = Mock()
        mock_row_2.model_version = "v1.3.0"
        mock_row_2.prediction_count = 120
        mock_row_2.average_churn_probability = 42.1
        mock_row_2.predicted_churn_count = 45
        mock_row_2.predicted_churn_rate = 37.5
        mock_row_2.high_risk_count = 30
        mock_row_2.medium_risk_count = 25
        mock_row_2.low_risk_count = 65

        mock_db = Mock()
        mock_db.execute = Mock(return_value=Mock(fetchall=Mock(return_value=[mock_row_1, mock_row_2])))

        res = await model.get_ab_test_results(
            versions=["v1.2.0-catboost", "v1.3.0"],
            db=mock_db,
            current_user={"username": "admin"}
        )

        assert "v1.2.0-catboost" in res["results"]
        assert "v1.3.0" in res["results"]

        catboost_res = res["results"]["v1.2.0-catboost"]
        assert catboost_res["prediction_count"] == 100
        assert catboost_res["average_churn_probability"] == 35.5
        assert catboost_res["predicted_churn_count"] == 30
        assert catboost_res["predicted_churn_rate"] == 30.0
        assert catboost_res["risk_distribution"] == {"high": 20, "medium": 15, "low": 65}
