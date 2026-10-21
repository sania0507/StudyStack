
def test_create_domain(client):
    response = client.post(
        "/domains",
        json={"name": "University"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "University"
    assert data["colour"] == "violet"
    assert "id" in data
    assert "user_id" in data


def test_list_domains(client):
    client.post("/domains", json={"name": "University"})
    client.post("/domains", json={"name": "Side Skills"})

    response = client.get("/domains")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_update_domain(client, domain_id):
    response = client.patch(
        f"/domains/{domain_id}",
        json={"name": "University Updated"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "University Updated"



def test_user_cannot_update_another_users_domain(
    client, second_user_client, domain_id
):
    response = second_user_client.patch(
        f"/domains/{domain_id}",
        json={"name": "Stolen Domain"},
    )

    assert response.status_code == 404
