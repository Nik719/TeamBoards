from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Company, KBEntry, QueryLog


# ─── Health ───────────────────────────────────────────────────────────────────

class HealthViewTest(TestCase):
    def test_returns_ok(self):
        response = APIClient().get('/api/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_no_auth_required(self):
        response = APIClient().get('/api/health/')
        self.assertNotEqual(response.status_code, 401)


# ─── Register ─────────────────────────────────────────────────────────────────

class RegisterViewTest(TestCase):
    URL = '/api/auth/register/'
    VALID = {
        'username': 'testcorp',
        'password': 'securepass123',
        'company_name': 'Test Corp',
        'email': 'test@testcorp.com',
    }

    def setUp(self):
        self.client = APIClient()

    def test_success_returns_201(self):
        r = self.client.post(self.URL, self.VALID, format='json')
        self.assertEqual(r.status_code, 201)

    def test_response_fields(self):
        r = self.client.post(self.URL, self.VALID, format='json')
        data = r.json()
        self.assertEqual(data['username'], 'testcorp')
        self.assertEqual(data['company_name'], 'Test Corp')
        self.assertEqual(data['role'], 'client')
        self.assertIn('api_key', data)
        self.assertIn('access', data)

    def test_duplicate_username_returns_400(self):
        self.client.post(self.URL, self.VALID, format='json')
        r = self.client.post(self.URL, self.VALID, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('username', r.json())

    def test_short_password_returns_400(self):
        r = self.client.post(self.URL, {**self.VALID, 'password': 'short'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('password', r.json())

    def test_invalid_email_returns_400(self):
        r = self.client.post(self.URL, {**self.VALID, 'email': 'not-an-email'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('email', r.json())

    def test_missing_company_name_returns_400(self):
        payload = {k: v for k, v in self.VALID.items() if k != 'company_name'}
        r = self.client.post(self.URL, payload, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('company_name', r.json())

    def test_signal_creates_company_with_api_key(self):
        self.client.post(self.URL, self.VALID, format='json')
        user = User.objects.get(username='testcorp')
        self.assertTrue(hasattr(user, 'company'))
        self.assertTrue(len(user.company.api_key) > 0)


# ─── Login ────────────────────────────────────────────────────────────────────

class LoginViewTest(TestCase):
    URL = '/api/auth/login/'

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='corp', password='securepass123', email='corp@example.com'
        )

    def test_success_returns_200(self):
        r = self.client.post(self.URL, {'username': 'corp', 'password': 'securepass123'}, format='json')
        self.assertEqual(r.status_code, 200)

    def test_response_contains_token_and_profile(self):
        r = self.client.post(self.URL, {'username': 'corp', 'password': 'securepass123'}, format='json')
        data = r.json()
        self.assertIn('access', data)
        self.assertEqual(data['username'], 'corp')
        self.assertIn('role', data)
        self.assertIn('api_key', data)

    def test_wrong_password_returns_401(self):
        r = self.client.post(self.URL, {'username': 'corp', 'password': 'wrongpass'}, format='json')
        self.assertEqual(r.status_code, 401)

    def test_unknown_user_returns_401(self):
        r = self.client.post(self.URL, {'username': 'nobody', 'password': 'securepass123'}, format='json')
        self.assertEqual(r.status_code, 401)

    def test_missing_password_returns_400(self):
        r = self.client.post(self.URL, {'username': 'corp'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('password', r.json())

    def test_missing_username_returns_400(self):
        r = self.client.post(self.URL, {'password': 'securepass123'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('username', r.json())


# ─── KB Query ─────────────────────────────────────────────────────────────────

class KBQueryViewTest(TestCase):
    URL = '/api/kb/query/'

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='client1', password='pass12345')
        self.client.credentials(HTTP_X_API_KEY=self.user.company.api_key)

        KBEntry.objects.create(
            question='What is Django?',
            answer='Django is a Python web framework.',
            category=KBEntry.Category.FRAMEWORK,
        )
        KBEntry.objects.create(
            question='What is PostgreSQL?',
            answer='PostgreSQL is a relational database.',
            category=KBEntry.Category.DATABASE,
        )
        KBEntry.objects.create(
            question='What is Docker?',
            answer='Docker packages apps into containers.',
            category=KBEntry.Category.CLOUD,
        )

    def test_search_matches_question(self):
        r = self.client.post(self.URL, {'search': 'Django'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['count'], 1)
        self.assertEqual(r.json()['results'][0]['category'], 'framework')

    def test_search_matches_answer(self):
        r = self.client.post(self.URL, {'search': 'relational database'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['count'], 1)

    def test_search_case_insensitive(self):
        r = self.client.post(self.URL, {'search': 'DJANGO'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['count'], 1)

    def test_no_results_returns_200_with_empty_list(self):
        r = self.client.post(self.URL, {'search': 'xyzzy_nonexistent'}, format='json')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['results'], [])
        self.assertEqual(data['total_pages'], 1)

    def test_blank_search_returns_400(self):
        r = self.client.post(self.URL, {'search': ''}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_missing_search_field_returns_400(self):
        r = self.client.post(self.URL, {}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        r = self.client.post(self.URL, {'search': 'Django'}, format='json')
        self.assertEqual(r.status_code, 401)

    def test_invalid_api_key_returns_401(self):
        self.client.credentials(HTTP_X_API_KEY='not-a-real-key')
        r = self.client.post(self.URL, {'search': 'Django'}, format='json')
        self.assertEqual(r.status_code, 401)

    def test_query_log_is_created(self):
        self.client.post(self.URL, {'search': 'Django'}, format='json')
        self.assertEqual(QueryLog.objects.count(), 1)
        log = QueryLog.objects.first()
        self.assertEqual(log.search_term, 'Django')
        self.assertEqual(log.results_count, 1)
        self.assertEqual(log.company, self.user.company)

    def test_query_log_records_zero_results(self):
        self.client.post(self.URL, {'search': 'xyzzy_nonexistent'}, format='json')
        log = QueryLog.objects.first()
        self.assertEqual(log.results_count, 0)

    def test_pagination_page_size(self):
        r = self.client.post(f'{self.URL}?page=1&page_size=2', {'search': 'a'}, format='json')
        data = r.json()
        self.assertLessEqual(len(data['results']), 2)
        self.assertEqual(data['page_size'], 2)

    def test_pagination_second_page(self):
        r1 = self.client.post(f'{self.URL}?page=1&page_size=2', {'search': 'a'}, format='json')
        r2 = self.client.post(f'{self.URL}?page=2&page_size=2', {'search': 'a'}, format='json')
        self.assertEqual(r1.json()['page'], 1)
        self.assertEqual(r2.json()['page'], 2)

    def test_page_size_capped_at_20(self):
        r = self.client.post(f'{self.URL}?page_size=999', {'search': 'a'}, format='json')
        self.assertEqual(r.json()['page_size'], 20)

    def test_response_includes_total_pages(self):
        r = self.client.post(f'{self.URL}?page_size=2', {'search': 'a'}, format='json')
        data = r.json()
        self.assertIn('total_pages', data)
        self.assertGreaterEqual(data['total_pages'], 1)

    def test_result_fields(self):
        r = self.client.post(self.URL, {'search': 'Django'}, format='json')
        result = r.json()['results'][0]
        for field in ('id', 'question', 'answer', 'category'):
            self.assertIn(field, result)


# ─── Admin Usage Summary ──────────────────────────────────────────────────────

class AdminUsageSummaryViewTest(TestCase):
    URL = '/api/admin/usage-summary/'

    def setUp(self):
        self.client = APIClient()

        self.admin_user = User.objects.create_user(username='admin_user', password='pass12345')
        admin_co = self.admin_user.company
        admin_co.role = Company.Role.ADMIN
        admin_co.save()

        self.client_user = User.objects.create_user(username='client_user', password='pass12345')

        QueryLog.objects.create(company=self.client_user.company, search_term='jwt', results_count=3)
        QueryLog.objects.create(company=self.client_user.company, search_term='jwt', results_count=2)
        QueryLog.objects.create(company=self.admin_user.company, search_term='docker', results_count=1)

    def _auth(self, user):
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}'
        )

    def test_admin_gets_200(self):
        self._auth(self.admin_user)
        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 200)

    def test_admin_response_fields(self):
        self._auth(self.admin_user)
        data = self.client.get(self.URL).json()
        self.assertEqual(data['total_queries'], 3)
        self.assertEqual(data['active_companies'], 2)
        self.assertIsInstance(data['top_search_terms'], list)

    def test_top_search_terms_ordered_by_count(self):
        self._auth(self.admin_user)
        terms = self.client.get(self.URL).json()['top_search_terms']
        self.assertEqual(terms[0]['search_term'], 'jwt')
        self.assertEqual(terms[0]['count'], 2)

    def test_top_search_terms_capped_at_5(self):
        for term in ('a', 'b', 'c', 'd', 'e', 'f'):
            QueryLog.objects.create(
                company=self.admin_user.company, search_term=term, results_count=0
            )
        self._auth(self.admin_user)
        terms = self.client.get(self.URL).json()['top_search_terms']
        self.assertLessEqual(len(terms), 5)

    def test_client_gets_403(self):
        self._auth(self.client_user)
        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 403)

    def test_unauthenticated_gets_401(self):
        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 401)
