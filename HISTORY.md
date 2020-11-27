## 0.2.4 (27.11.2020)

- Bugfix: serializing to json on a BaseDBMixin with child DBPydanticMixin's fails. PR #34 by @dhensen

## 0.2.3 (07.10.2020)

- Summary grammar fix. PR #28 by @languitar
- Skip setuptools 50.0 because of a pip/setuptools related issue. PR #32 by @dhensen
- Fix project formatters. PR #33 by @i8enn
- Fix BaseMongoDBDecoder for documents with arrays of simple type. PR #30 by @antipooh
- Add MongoDB encoder: Decimal to Decimal128. PR #31 by @dhensen
- Add passing in optional parameters of AsyncIOMotorClient. PR #29 by @dhensen

## 0.2.2 (24.07.2020)

- Fix missing nested packages in build by @i8enn

## 0.2.1 (24.07.2020)

- Created MongoDB encoders for encode queries or model to MongoDB driver. PR #24 by @i8enn
- Fix creating empty `id` field in models. Fix issue #23. PR #25 by @i8enn
- Created MongoDB decoders. PR #25 by @i8enn
- Changed pytest and coverage configuration. PR #25 by @i8enn

## 0.2 (21.07.2020)

* Implemented `id` public property for `PydanticDBMixin`. Updated *db mixins* and their tests. PR #17 by @i8enn
* Implemented Enum support. PR #20 by @i8enn 
* Replaces package manager from Pipenv to Poetry. PR #21 by @i8enn 

## 0.1.6 (20.01.2020)

* Fix arguments type in `update_many` method from `PydanticDBMixin`. PR #16 by @i8enn


## 0.1.5 (18.01.2020)

* Implemented `update_many` method in `PydanticDBMixin`. PR #15 by @i8enn


## 0.1.4 (30.12.2019)

* Allow to Mongo DB connect with default system settings and Unix domain socket. PR #11 by @hongquan


## 0.1.3 (10.12.2019)

* Implemented of set to field Pydantic model instance if field type is Pydantic model in reload method. PR #9 by @i8enn


## 0.1.2 (09.12.2019)

* Added json encoder for `ObjectIdStr` field in `DBPydanticMixin`. PR #4 by @i8enn
* Changed PyPi token in Travis config


## 0.1.1 (08.12.2019)

* Updated stage run rules in Travis config. Updated `setup.py` PR #3 by @i8enn


## 0.1.0 (05.12.2019)

* Implemented singleton interface (`MongoDBManager`) for mongodb connections. PR #2 by @i8enn
* Implemented `DBPydanticMixin`. PR #2 by @i8enn
* Included Travis config and implemented deployment to PyPi. PR #2 by @i8enn