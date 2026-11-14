import os

# Base SQLite indépendante pour les tests automatisés.
# Elle ne doit jamais utiliser la base de développement.
os.environ["DATABASE_URL"] = "sqlite:///./dentardv_test.db"
os.environ["JWT_SECRET"] = "test-secret-for-automated-tests-only"
os.environ["ADMIN_IDENTIFIANT"] = "admin-test"
os.environ["ADMIN_PASSWORD"] = "Admin-test-2026"
os.environ["DEMO_PASSWORD"] = "Demo-test-2026"
