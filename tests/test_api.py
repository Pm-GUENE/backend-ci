import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200


def test_liste_dentistes_accessible(client):
    response = client.get("/dentistes")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_liste_soins_accessible(client):
    response = client.get("/soins")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_connexion_refuse_mauvais_identifiants(client):
    response = client.post(
        "/connexion",
        json={
            "identifiant": "utilisateur-inexistant",
            "mot_de_passe": "mauvais-mot-de-passe"
        }
    )

    assert response.status_code == 401

def obtenir_jeton(client, identifiant, mot_de_passe):
    response = client.post("/connexion", json={
        "identifiant": identifiant,
        "mot_de_passe": mot_de_passe,
    })
    assert response.status_code == 200
    return response.json()["access_token"]


def test_connexion_administrateur_reussie(client):
    response = client.post("/connexion", json={
        "identifiant": "admin-test",
        "mot_de_passe": "Admin-test-2026",
    })

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert response.json()["doit_changer_mdp"] is False


def test_connexion_dentiste_reussie(client):
    response = client.post("/connexion", json={
        "identifiant": "moustapha.diaw",
        "mot_de_passe": "Demo-test-2026",
    })

    assert response.status_code == 200
    assert response.json()["role"] == "dentiste"
    assert response.json()["doit_changer_mdp"] is False


def test_route_admin_acceptee_pour_administrateur(client):
    token = obtenir_jeton(client, "admin-test", "Admin-test-2026")

    response = client.get(
        "/admin/dentistes",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_route_admin_refusee_pour_dentiste(client):
    token = obtenir_jeton(
        client, "moustapha.diaw", "Demo-test-2026"
    )

    response = client.get(
        "/admin/dentistes",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_route_admin_refusee_sans_authentification(client):
    response = client.get("/admin/dentistes")

    assert response.status_code == 401


def test_route_dentiste_refusee_pour_administrateur(client):
    token = obtenir_jeton(client, "admin-test", "Admin-test-2026")

    response = client.get(
        "/mes-rendez-vous",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_route_dentiste_acceptee_pour_dentiste(client):
    token = obtenir_jeton(
        client, "moustapha.diaw", "Demo-test-2026"
    )

    response = client.get(
        "/mes-rendez-vous",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_route_dentiste_refusee_sans_authentification(client):
    response = client.get("/mes-rendez-vous")

    assert response.status_code == 401
