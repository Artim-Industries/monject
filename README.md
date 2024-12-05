
# Monject

Monject is an Object Mapper for MongoDB, designed to simplify the interaction with MongoDB databases by providing an intuitive and Pythonic interface. Monject is primarly designed as an fastapi extension but can also be used without fastapi.

[![PyPI version](https://img.shields.io/pypi/v/monject.svg)](https://pypi.org/project/monject/)
[![License](https://img.shields.io/pypi/l/monject.svg)](https://github.com/ArtimIndustries/monject/blob/main/LICENSE)

## Features

- **Object Mapping**: Map MongoDB documents to Python objects.
- **Foreign Key Relationships**: Support for various types of foreign key relationships including `ForeignKey`, `MultiForeignKey`, `EmbeddedMultiForeignKey`, `EmbeddedMultiToMultiForeignKey` and `NestedConditionedForeignKey`.
- **CRUD Operations**: Easily perform Create, Read, Update, and Delete operations.
- **Pagination**: Built-in support for paginated queries.
- **Security**: Token-based authentication and password hashing.

## Installation

To install the required dependencies, run:

```sh
pip install monject
```

## Usage

### Object Manager

The `ObjectManager` class is the core of Monject. It provides methods to interact with MongoDB collections.

#### Example

```python
from monject.ObjectManager import ObjectManager
from bson import ObjectId

class User(ObjectManager):
    _id = ObjectId
    fullName = str()
    email = str()
    password = str()
    # ... all required fields
    
    class Meta:
        __collection__ = 'users' # Here the collection 

    def __init__(self):
        self._id = ObjectId() # Important!
        super().__init__() # Important!

    def __str__(self):
        return self.email

    def __repr__(self):
        return self.email

    def __eq__(self, other):
        return self._id == other._id

    def __hash__(self):
        return hash(self._id)


user = User().objects.get("some_user_id")
print(user)

# get specific
users = User().objects.filter({}, items=0, pages=0) # use mongodb query for filtering

# get all
users = User().objects.all(items=0, pages=0) # items, pages for pagination, set items=0 to disable

# update
user = User().objects.get("some_user_id")
setattr(user, "email", "john@doe.com")
user.objects.update()

# delete
user = User().objects,get("some_user_id")
user.objects.delete()
```

### Foreign Key Relationships

Monject supports various types of foreign key relationships:

- `ForeignKey`

```json
{
    "title": "Test",
    "author": "someObjectID" // author = ObjectManager.ForeignKey(UserModel)
}
```

- `MultiForeignKey`

```json
{
    "title": "Test",
    "authors": ["someObjectID", "someOtherObjectId"] // authors = ObjectManager.MultiForeignKey(UserModel)
}
```

- `EmbeddedMultiForeignKey`
```json
{
    "title": "Test",
    "authors": {
        "userList": ["someObjectID", "someOtherObjectId"]
    } // authors = ObjectManager.EmbeddedMultiForeignKey(UserModel, "authors.userList")
}
```

- `EmbeddedMultiToMultiForeignKey`
```json
{
    "title": "Test",
    "authors": {
        "userList": ["someObjectID", "someOtherObjectId"],
        "otherList": ["1", "2"]
    } // authors = ObjectManager.EmbeddedMultiToMultiForeignKey([UserModel, OtherModel], ["authors.userList", "authors.otherList"])
}
```

- `NestedConditionedForeignKey`
```json
{
    "title": "Test",
    "authors": {
        {
            "value": "HereAnObjectID",
            "type": "primary",
            // ...
        }, 
        {
            "value": "HereAnObjectID",
            "type": "primary",
            // ...
        }, 
        {
            "value": "HereAnObjectID",
            "type": "secondary",
            // ...
        }, 
    } // authors = ObjectManager.NestedConditionedForeignKey("value", UserModel, "type", "primary|secondary") // primary|secondary is a regexp
}
```

#### Example

```python
class Post(ObjectManager):
    _id = ObjectId
    author = str()
    # ...

    class Meta:
        __collection__ = "posts"
        author = ObjectManager.ForeignKey(User)
        # fieldNameOfModel = ObjectManager.FOREIGN_RELEATIONSHIP(modalClassOfReplacement)

    # ...

# get one Specific
post = Post().objects.get("some_post_id")
print(post)


```

### Exporting the objects for displaying in web etc.

You'll need to export the objects to display them for example on a webpage / fastapi backend

#### Example

```python

class Post(ObjectManager):
    _id = ObjectId
    author = str()
    # ...

    class Meta:
        __collection__ = "posts"
        author = ObjectManager.ForeignKey(User)
        # fieldNameOfModel = ObjectManager.FOREIGN_RELEATIONSHIP(modalClassOfReplacement)

    # ...

# get one Specific
post = Post().objects.get("some_post_id")

# export one object
return post.objects.export()

# get all
posts = Post().objects.all(items=0, pages=0) # items, pages for pagination, set items=0 to disable

# if there is more than one to export you'll need to do it like that:
posts["data"] = [post.objects.export() for post in posts["data"]]
return posts

```

### Using Monject's Security

Monject includes a `Security` class for handling token-based authentication and password hashing.

#### Security Configuration

Monject uses a `config.ini` file for security configuration. Ensure you have a `config.ini` file with the following structure included:

```ini

[TOKEN_SECRET]
secret = "A SECRET FOR YOUR TOKENS"

[TOKEN_EXPIRATION]
expiration = 2592000000 # An Expiration Period

```

#### Example

```python
from monject.Security import Security

class User(ObjectManager):
    # ...

security = Security()
hashed_password = security.hashPassword("my_password", "my_secret")
token = security.issueToken(User().objects.get("someRandomUserId")) 
is_valid = security.checkToken(token, User) # User is just the Usermodel
currentUser = security.getCurrentUser(token, User) # User is just the Usermodel
```

## Configuration

Monject uses a `config.yml` file for database configuration. Ensure you have a `config.yml` file with the following structure:

```yaml
Database:
  - host: "localhost"
  - port: 27017
  - username: "your_username"
  - password: "your_password"
  - database: "your_database"
```

## Example Project Structure with fastapi
```
/
- ...
- models // Define every model in a seperate File
    - User.py
    - Post.py
    - ...
- routers // have for every model a router including following features: getAll, getSpecific, update, delete
    - users.py
    - posts.py
    - me.py
    - ...
- index.py
- ...
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

## Contact

For any inquiries, please contact [Artim Industries](mailto:mauritzlemgen@artim-industries.com).
