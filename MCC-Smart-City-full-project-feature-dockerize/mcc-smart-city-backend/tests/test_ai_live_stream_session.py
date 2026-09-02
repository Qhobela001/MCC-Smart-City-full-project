import unittest

from fastapi.routing import APIRoute

from app.modules.live_streams.router import router
from app.modules.ai_detections.machine_auth import require_ai_worker


class AILiveStreamSessionTests(unittest.TestCase):
    def test_machine_session_route_is_private_and_machine_authenticated(self):
        target = "/live-streams/ai/cameras/{camera_identifier}/session"
        route = next(
            item
            for item in router.routes
            if isinstance(item, APIRoute) and item.path == target
        )
        self.assertIn("POST", route.methods)
        self.assertFalse(route.include_in_schema)
        dependency_calls = {dependency.call for dependency in route.dependant.dependencies}
        self.assertIn(require_ai_worker, dependency_calls)


if __name__ == "__main__":
    unittest.main()
