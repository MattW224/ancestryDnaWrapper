# AncestryDNA API wrapper

Ancestry exposes an undocumented REST API for its DNA features. This Python wrapper inventories the available calls, and exposes it to novice developers or power users in a more intuitive manner. I have consciously tried to keep the method names and parameters self-explanatory, but included the documentation below if additional context is needed.

## Introduction
Many DNA function calls require you to obtain and input GUIDs corresponding to tests and cousin matches. Later revisions of this wrapper might simplify this process, translating human-readable values to their GUIDs.

This wrapper assumes intermediate knowledge of Python -- for example, being able to read the `ancestryDnaWrapper` class definition, and knowing to input the username and password values to authenticate successfully. 

## Authentication
Initializing the `ancestryDnaWrapper` class will automatically perform authentication. It will authenticate the US-based endpoint by default. This can be overrided with the `endpoint` keyword argument.

## Selecting tests
Any of the group, star, and test require a test to be selected. The wrapper will not default to anything.

* `get_tests` -- will enumerate all completed tests registered to the account. By default, this will not include any tests shipped, or awaiting processing. To see other tests, change the `test_type` parameter (default value is `complete`).
* `use_test` -- every object returned from `get_tests` will include a `guid` property. That property must be inputted to use any latter options. Like the Ancestry UI, you cannot select more than one test.

## Test operations
* `get_dna_matches` -- This will return **all** DNA matches. Every DNA match will contain a `testGuid` attribute. The method also contains a `shared_with_test_id` attribute. To obtain shared matches, input `testGuid` there.
* `get_admixture`-- This will return your admixture (e.g. 100% Martian). The method also contains a `comparison_guid` attribute. To compare admixture with another user, input their `testGuid` there.

## Group operations
* `get_custom_groups` -- This will return all custom groups you created. If you do not have any, it will return an empty array. Each object will contain ` tagId` attribute -- required in any `delete` or `modify` operations. 
* `create_custom_group` -- This creates a custom group for you to categorize your matches. Include a name and color value (e.g. `#FFFFFF`). The response object will include a `tagId` attribute, needed for addition/deletion operations.
* `delete_custom_group` -- deletes group corresponding to the `tagId`. If creating, and then immediately deleting groups, you may encounter eventual consistency issues. Ensure you wait ~ 30 seconds before attempting operations.
* `modify_group_membership` -- add or remove DNA matches to a custom group. Obtain the `testGuid` from `get_dna_matches` and the `tagId` from `create/get_custom_group`. Action will be `add` or `remove`.

## Star operation
* `modify_star` -- enables you to favorite a match by starring it. Obtain the `testGuid` from `get_dna_matches`. Action will be `add` or `remove`.