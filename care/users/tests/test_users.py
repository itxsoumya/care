import pytest

from care.users.models import User


@pytest.fixture()
def data():
    return {
        "user_type": 5,
        "email": "some.email@somedomain.com",
        "phone_number": "5554446667",
        "age": 30,
        "gender": 1,
        "district": 11,
        "username": "foo",
        "password": "bar",
    }


@pytest.mark.usefixtures("district_data")
@pytest.mark.django_db(transaction=True)
class TestUser:
    def test_superuser_can_read_modify_delete_all(self, client, user, data):
        user.is_superuser = True
        user.save()

        response = client.post("/api/v1/users/", data,)
        assert response.status_code == 201
        newuser = response.json()
        password = data.pop("password")

        client.force_authenticate(user=user)

        response = client.get("/api/v1/users/")
        assert response.status_code == 200
        assert response.json()["count"] == 2
        assert response.json()["results"][0]["username"] == user.username
        assert {
            **data,
            "id": newuser["id"],
            "district": 11,
            "gender": "Male",
            "user_type": "Doctor",
            "first_name": "",
            "last_name": "",
        } == response.json()["results"][1], "reading others is not limited"

        response = client.get(f"/api/v1/users/{data['username']}/")
        assert response.status_code == 200
        assert response.json() == {
            **data,
            "id": newuser["id"],
            "district": 11,
            "gender": "Male",
            "user_type": "Doctor",
            "first_name": "",
            "last_name": "",
        }, "reading others is not limited"

        response = client.put(f"/api/v1/users/{data['username']}/", {**data, "age": 31, "password": password,})
        assert response.status_code == 200
        assert response.json()["age"] == 31
        assert User.objects.only("age").get(username=data["username"]).age == 31

        response = client.delete(f"/api/v1/users/{data['username']}/")
        assert response.status_code == 204
        with pytest.raises(User.DoesNotExist):
            User.objects.get(username=data["username"])

    def test_user_can_read_cant_modify_delete_others(self, client, user, data):
        response = client.post("/api/v1/users/", data,)
        assert response.status_code == 201
        newuser = response.json()

        client.force_authenticate(user=user)

        response = client.get("/api/v1/users/")
        assert response.status_code == 200
        assert response.json()["count"] == 2
        assert response.json()["results"][0]["id"] == user.id
        assert response.json()["results"][1] == {
            "id": newuser["id"],
            "first_name": newuser["first_name"],
            "last_name": newuser["last_name"],
        }, "reading others is limited"

        response = client.get(f"/api/v1/users/{data['username']}/")
        assert response.status_code == 200
        assert response.json() == {
            "id": newuser["id"],
            "first_name": newuser["first_name"],
            "last_name": newuser["last_name"],
        }, "reading others is limited"

        response = client.put(f"/api/v1/users/{data['username']}/", data)
        assert response.status_code == 404

        response = client.delete(f"/api/v1/users/{data['username']}/")
        assert response.status_code == 404

    def test_user_can_read_modify_delete_himself(self, client, data):
        response = client.post("/api/v1/users/", data,)
        assert response.status_code == 201

        user = User.objects.get(username=data["username"])
        password = data.pop("password")
        client.force_authenticate(user=user)

        response = client.get("/api/v1/users/")
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert user.id in {r["id"] for r in response.json()["results"]}

        response = client.get(f"/api/v1/users/{user.username}/")
        assert response.status_code == 200
        assert response.json() == {
            **data,
            "id": user.id,
            "district": 11,
            "gender": "Male",
            "user_type": "Doctor",
            "first_name": "",
            "last_name": "",
        }

        response = client.put(f"/api/v1/users/{user.username}/", {**data, "age": 31, "password": password})
        assert response.status_code == 200
        assert response.json()["age"] == 31
        assert User.objects.only("age").get(username=data["username"]).age == 31

        response = client.delete(f"/api/v1/users/{user.username}/")
        assert response.status_code == 204
        with pytest.raises(User.DoesNotExist):
            User.objects.get(username=data["username"])
