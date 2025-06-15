from bson import ObjectId
import re
from .Connection import Connection
from fastapi import HTTPException
import copy

class ObjectManager:
    def __init__(self):
        # Instantiate objects with the collection name
        self.objects = self.objects(self.get_meta(), self.get_class(), self.get_object())

    def get_meta(self):
        return self.__class__.Meta
    
    def get_class(self):
        return self.__class__
    
    def get_object(self):
        return self

    class objects:
        def __init__(self, meta, parentClass, parentObject):
            self.meta = meta
            self.parentClass = parentClass
            self.parentObject = parentObject
            self.exported = False
            self.runs = 0
            self.level = 0
            self.__collection__ = meta.__collection__
            
        def instantiate(self, content: dict, status: int = 0):
            keysOfObject = [{key: self.parentClass.__dict__[key]} for key in self.parentClass.__dict__ if not key.startswith("__") and key != "objects" and key != "Meta"]
            

            for key in keysOfObject:
                for key in key:
                    value = self.parentClass.__dict__[key]
                    
                    if str(type(value)) == "<class 'type'>" and status == 0:
                        continue
                    
                    if key in content:
                        setattr(self.parentObject, key, content[key])
                    else:
                        if key == "_id":
                            value = str(value)
                        
                        setattr(self.parentObject, key, value)
            
            return self.parentObject

        def get_from_path(self, data, path):
            keys = path.split('.')  # Zerlege den Pfad in seine Schlüssel
            for key in keys:
                if isinstance(data, dict):
                    data = data.get(key)  # Greife auf den nächsten Schlüssel zu
                else:
                    return None  # Falls es keine dict-Struktur mehr ist, abbrechen
            return data

        def set_in_path(self, data, path, value):
            keys = path.split('.')
            for key in keys[:-1]:  # Gehe durch alle Keys außer den letzten
                if isinstance(data, dict):
                    data = data.get(key)
                else:
                    return  # Abbruch, falls keine dict-Struktur mehr vorhanden ist
            data[keys[-1]] = value  # Setze den Wert beim letzten Schlüssel


        def recursive(self, obj, depth = 10):
            final = {}
            
            self.runs += 1
            if self.runs > depth:
                return final
  
            for key in dir(obj):                
                conditionAccepted = False
                if key.startswith("__"):
                    continue
            
                if key == "objects" or key == "Meta":
                    continue

                if str(type(getattr(obj, key))).startswith("<class 'method") or str(type(getattr(obj, key))).startswith(
                        "<class 'type"):
                    continue
                
                if not hasattr(obj, "Meta"):
                    continue

                if hasattr(obj.Meta, key) and isinstance(getattr(obj.Meta, key), ObjectManager.ForeignKey):
                    conditionAccepted = True
                    final[key] = self.recursive(getattr(obj, key))

                if hasattr(obj.Meta, key) and isinstance(getattr(obj.Meta, key), ObjectManager.MultiForeignKey):
                    conditionAccepted = True
                    document = obj.__dict__
                    final[key] = []
                    for doc in document[key]:
                        final[key].append(self.recursive(doc))

                if hasattr(obj.Meta, key) and isinstance(getattr(obj.Meta, key), ObjectManager.EmbeddedMultiForeignKey):
                    path = getattr(obj.Meta, key).path
                    path = path.split('.') if isinstance(path, str) else path

                    for p in path:
                        obj = obj[p]

                    for doc in obj:
                        final[obj.index(doc)] = self.recursive(doc)

                if hasattr(obj.Meta, key) and isinstance(getattr(obj.Meta, key), ObjectManager.EmbeddedMultiToMultiForeignKey):
                    conditionAccepted = True
                    paths = getattr(obj.Meta, key).paths
                    document = obj.__dict__
                    for path in paths:
                        current_level = self.get_from_path(document, path)  # Hole den verschachtelten Wert

                        if current_level is not None:
                            for i, doc in enumerate(current_level):
                                if hasattr(doc, "Meta"):
                                    current_level[i] = self.recursive(doc)  # Modifikation

                            # Setze den modifizierten Wert zurück ins Dokument
                            self.set_in_path(document, path, current_level)

                    final[key] = document[key]

                if hasattr(obj.Meta, key) and isinstance(getattr(obj.Meta, key), ObjectManager.NestedConditionedForeignKey):
                    conditionAccepted = True
                    document = obj.__dict__
                    listOfObjects = document[key]
                    targetField = getattr(self.meta, key).target

                    print(listOfObjects, document, key, targetField)
                    for _obj in listOfObjects:
                        regexOfCondition = re.compile(getattr(self.meta, key).conditionValue)
                        keyForCondition = getattr(self.meta, key).conditionKey

                        if re.search(regexOfCondition, _obj[keyForCondition]):
                            document[key][listOfObjects.index(_obj)][targetField] = self.recursive(_obj[targetField])

                    final[key] = document[key]

                if not conditionAccepted:
                    if key == "_id":
                        final[key] = str(getattr(obj, key))
                        continue
                    
                    final[key] = getattr(obj, key)
            
            return self.IdCheck(final)
        
        def IdCheck(self, _dict: dict):
            self.level += 1

            if self.level > 100:
                return _dict
            
            for key, value in _dict.items():
                if isinstance(value, dict):
                    _dict[key] = self.IdCheck(value)
                elif isinstance(value, list):
                    for index, item in enumerate(value):
                        if isinstance(item, dict):
                            _dict[key][index] = self.IdCheck(item)
                        elif isinstance(item, ObjectId):
                            _dict[key][index] = str(item)
                elif isinstance(value, ObjectId):
                    _dict[key] = str(value)

                
                
            return _dict

        def export(self):
            if self.exported == True:
                print("Only one export per object is allowed.")
            
            self.exported = True
            return self.recursive(self.parentObject)

        @staticmethod
        def foreignKey(identifier, document, key):
            identi = identifier()

            document[key] = identi.objects.get(document[key])

            return document

        @staticmethod
        def multiForeignKey(identifier, document, key):
            identi = identifier()

            newDocument = []  
            index = 0
            for doc in document[key]:
                fetched = identi.objects.get(doc)
                fetched = copy.deepcopy(fetched)

                newDocument.append(fetched)
                index += 1
            
            document[key] = newDocument
            return document

        def embeddedMultiForeignKey(self, identifier, document, key):
            path = getattr(self.meta, key).path
            path = path.split('.') if isinstance(path, str) else path

            for p in path:
                document = document[p]

            identi = identifier()
            newDocument = []
            for doc in document:
                newDocument.append(identi.objects.get(doc))
            
            document = newDocument

            return document

        def embeddedMultiToMultiForeignKey(self, identifier, document, key):
            paths = getattr(self.meta, key).paths
            for path in paths:
                index = paths.index(path)
                identify = identifier[index]

                path = path.split('.') if isinstance(path, str) else path

                embed = document
                for p in path:
                    embed = embed[p] if isinstance(embed, dict) else embed

                identi = identify()
                for doc in embed:
                    if not isinstance(doc, str):
                        continue

                    embed[embed.index(doc)] = identi.objects.get(doc)

            return document

        def nestedConditionedForeignKey(self, identifier, document, key):
            listOfObjects = document[key]
            targetField = getattr(self.meta, key).target
            for obj in listOfObjects:
                regexOfCondition = re.compile(getattr(self.meta, key).conditionValue)
                keyForCondition = getattr(self.meta, key).conditionKey

                if re.search(regexOfCondition, obj[keyForCondition]):
                    identi = identifier()
                    document[key][listOfObjects.index(obj)][targetField] = identi.objects.get(obj[targetField])

            return document

        def toDict(self):
            return self.__dict__

        def get(self, _id):
            if _id == "" or _id == None:
                return None
            document = Connection().getDocument(self.__collection__, {"_id": ObjectId(_id)})
  
            for key in dir(self.meta):
                if key.startswith("_"):
                    continue
                
                if key == "_id":
                    document["_id"] = str(document["_id"])

                identifier = getattr(self.meta, key).identifier

                print("Here 1")

                if isinstance(getattr(self.meta, key), ObjectManager.ForeignKey):
                    document = self.foreignKey(identifier, document, key)

                if isinstance(getattr(self.meta, key), ObjectManager.MultiForeignKey):
                    document = self.multiForeignKey(identifier, document, key)
                
                print(document)

                if isinstance(getattr(self.meta, key), ObjectManager.EmbeddedMultiForeignKey):
                    document = self.embeddedMultiForeignKey(identifier, document, key)

                if isinstance(getattr(self.meta, key), ObjectManager.EmbeddedMultiToMultiForeignKey):
                    document = self.embeddedMultiToMultiForeignKey(identifier, document, key)

                if isinstance(getattr(self.meta, key), ObjectManager.NestedConditionedForeignKey):
                    document = self.nestedConditionedForeignKey(identifier, document, key)

            
            
            return self.instantiate(document, 1)

        def filter(self, query, items: int = 30, page: int = 0):
            data = Connection().getDocuments(self.__collection__, query, items, page)

            for key in dir(self.meta):
                if key.startswith("_"):
                    continue
                
                if self.meta.__dict__[key] == "":
                    continue

                identifier = getattr(self.meta, key).identifier
                if isinstance(getattr(self.meta, key), ObjectManager.ForeignKey):
                    for document in data["data"]:
                        data["data"][data["data"].index(document)] = self.foreignKey(identifier, document, key)

                if isinstance(getattr(self.meta, key), ObjectManager.MultiForeignKey):
                    for document in data["data"]:
                        data["data"][data["data"].index(document)] = self.multiForeignKey(identifier, document, key)

                if isinstance(getattr(self.meta, key), ObjectManager.EmbeddedMultiForeignKey):
                    for document in data["data"]:
                        data["data"][data["data"].index(document)] = self.embeddedMultiForeignKey(identifier, document, key)

                if isinstance(getattr(self.meta, key), ObjectManager.EmbeddedMultiToMultiForeignKey):
                    for document in data["data"]:
                        data["data"][data["data"].index(document)] = self.embeddedMultiToMultiForeignKey(identifier, document, key)

                if isinstance(getattr(self.meta, key), ObjectManager.NestedConditionedForeignKey):
                    for document in data["data"]:
                        data["data"][data["data"].index(document)] = self.nestedConditionedForeignKey(identifier, document, key)
            
            data["data"] = [copy.deepcopy(self.instantiate(document, 1)) for document in data["data"]]
            
            return data

        def all(self, items: int = 0, page: int = 0):
            data = Connection().getCollection(self.__collection__, items, page)

            for key in dir(self.meta):
                if key.startswith("_"):
                    continue

                if key == "_id":
                    dir(self.meta).__dict__[key] = str(dir(self.meta).__dict__[key])

                identifier = getattr(self.meta, key).identifier

                if isinstance(getattr(self.meta, key), ObjectManager.ForeignKey):
                    for document in data["data"]:
                        data["data"][data["data"].index(document)] = self.foreignKey(identifier, document, key)

                if isinstance(getattr(self.meta, key), ObjectManager.MultiForeignKey):
                    for document in data["data"]:
                        data["data"][data["data"].index(document)] = self.multiForeignKey(identifier, document, key)

                if isinstance(getattr(self.meta, key), ObjectManager.EmbeddedMultiForeignKey):
                    for document in data["data"]:
                        data["data"][data["data"].index(document)] = self.embeddedMultiForeignKey(identifier, document, key)

                if isinstance(getattr(self.meta, key), ObjectManager.EmbeddedMultiToMultiForeignKey):
                    for document in data["data"]:
                        data["data"][data["data"].index(document)] = self.embeddedMultiToMultiForeignKey(identifier, document, key)

                if isinstance(getattr(self.meta, key), ObjectManager.NestedConditionedForeignKey):
                    for document in data["data"]:
                        data["data"][data["data"].index(document)] = self.nestedConditionedForeignKey(identifier, document, key)
            
            data["data"] = [copy.deepcopy(self.instantiate(document, 1)) for document in data["data"]]

            return data

        def save(self):
            """
            Saves the current state of the object by creating a dictionary of its attributes.
            The method performs the following steps:
            1. Collects attributes from the parent object and parent class.
            2. Filters out certain attributes based on specific conditions.
            3. Constructs a final dictionary of attributes to be saved.
            Returns:
                dict: A dictionary containing the filtered attributes of the object.
            """
            _final = {}
            
            for key in dir(self.parentObject):
                _final[key] = getattr(self.parentObject, key)
            
            for key in dir(self.parentClass):
                
                if key == "objects" or key == "Meta":
                    continue
                
                if key in _final and key != "_id":
                    continue
                
                if key.startswith("__") and key != "_id":
                    continue
                        
                _final[key] = getattr(self.parentClass, key)
            
            _final = {key: _final[key] for key in _final if not key.startswith("__")}
            keysOfForeignKeys = [key.upper() for key in self.__class__.__dict__]

            final = {}
            for key in _final:
                if key.upper() in keysOfForeignKeys and key != "_id":
                    continue
                
                if key == "objects" or key == "Meta":
                    continue
                                
                if str(type(_final[key])) == "<class 'method'>":
                    continue
                
                final[key] = _final[key]
                
            final["_id"] = getattr(self.parentObject, "_id")

            
            return Connection().saveDocument(self.__collection__, final)

        def update(self):
            """
            Updates the current state of the object by creating a dictionary of its attributes.
            The method performs the following steps:
            1. Collects attributes from the parent object and parent class.
            2. Filters out certain attributes based on specific conditions.
            3. Constructs a final dictionary of attributes to be saved.
            Returns:
                dict: A dictionary containing the filtered attributes of the object.
            """
            _id = getattr(self.parentObject, "_id")
            print(_id)
            _final = {}
            
            for key in dir(self.parentObject):
                _final[key] = getattr(self.parentObject, key)
             
            
            for key in dir(self.parentClass):
                
                if key == "objects" or key == "Meta":
                    continue
                
                if key in _final and key != "_id":
                    continue
                
                if key.startswith("__") and key != "_id":
                    continue
                        
                _final[key] = getattr(self.parentClass, key)
            
  
            _final = {key: _final[key] for key in _final if not key.startswith("__")}
            keysOfForeignKeys = [key.upper() for key in self.__class__.__dict__]

            allKeysOfForeignKeys = [elem for elem in _final["Meta"].__dict__ if not elem.startswith("__")]
            allTypesOfForeignKeys = [type(_final["Meta"].__dict__[elem]) for elem in allKeysOfForeignKeys if not elem.startswith("__")]

            __final = copy.deepcopy(_final)
            for index, key in enumerate(allKeysOfForeignKeys):
                if allTypesOfForeignKeys[index] == ObjectManager.ForeignKey:
                    __final[key] = _final[key]._id

                if allTypesOfForeignKeys[index] == ObjectManager.MultiForeignKey:
                    __final[key] = [_final[key][i]._id for i in range(len(_final[key]))]

                if allTypesOfForeignKeys[index] == ObjectManager.EmbeddedMultiForeignKey:
                    print("Hint: EmbeddedMultiForeignKey is currently not supported in update method. Please check that your objects are ids as strings.")

                if allTypesOfForeignKeys[index] == ObjectManager.EmbeddedMultiToMultiForeignKey:
                    print("Hint: EmbeddedMultiToMultiForeignKey is currently not supported in update method. Please check that your objects are ids as strings.")


                if allTypesOfForeignKeys[index] == ObjectManager.NestedConditionedForeignKey:
                    print("Hint: NestedConditionedForeignKey is currently not supported in update method. Please check that your objects are ids as strings.")


            final = {}
            for key in __final:
                if key.upper() in keysOfForeignKeys and key != "_id":
                    continue
                
                if key == "objects" or key == "Meta":
                    continue
                                
                if str(type(__final[key])) == "<class 'method'>":
                    continue
                
                final[key] = __final[key]
            
            return Connection().updateDocument(self.__collection__, {"_id": ObjectId(_id)}, final)
        
        def delete(self):
            """
            Deletes the current object from the database.
            Returns:
                dict: A dictionary containing the status of the deletion operation.
            """
            _id = getattr(self.parentObject, "_id")    
            return Connection().deleteDocument(self.__collection__, {"_id": ObjectId(_id)})

    class ForeignKey:
        """
            A class to represent a ForeignKey relationship.

            Attributes:
            ----------
            identifier : object
                The identifier for the foreign key relationship.
        """
        def __init__(self, identifier):
            self.identifier = identifier

    class MultiForeignKey:
        """
            A class to represent a Multi ForeignKey relationship.

            Attributes:
            ----------
            identifier : object
                The identifier for the foreign key relationship.
        """
        def __init__(self, identifier):
            self.identifier = identifier

    class EmbeddedMultiForeignKey:
        """
            A class to represent an Embedded Multi ForeignKey relationship.

            Attributes:
            ----------
            identifier : object
                The identifier for the foreign key relationship.
            path : str
                The path to the embedded documents.
        """
        def __init__(self, identifier: object, path: str):
            self.identifier = identifier
            self.path = path

    class EmbeddedMultiToMultiForeignKey:
        """
            A class to represent an Embedded Multi-to-Multi ForeignKey relationship.

            Attributes:
            ----------
            identifiers : list
                The list of identifiers for the foreign key relationship.
            paths : list
                The list of paths to the embedded documents.
        """
        def __init__(self, identifiers: list, paths: list):
            self.identifier = identifiers
            self.paths = paths

    class NestedConditionedForeignKey:
        """
            A class to represent a Nested Conditioned ForeignKey relationship.

            Attributes:
            ----------
            identifier : object
                The identifier for the foreign key relationship.
            condition : dict
                The condition for the foreign key relationship.
        """
        def __init__(self, identifier, target, conditionKey, conditionValue):
            self.identifier = identifier
            self.target = target
            self.conditionKey = conditionKey
            self.conditionValue = conditionValue
