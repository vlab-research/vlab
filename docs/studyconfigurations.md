# Study Configurations

This is the documented standard for interface used in studies. Please open
a Pull Request here to discuss any proposed changes

Creating a study consists of configuring a lot of different variables,
separated into groups.

All studies require the following configurations:

1. [General](#general)
2. [Destination](#destination)
3. [Recruitment](#recruitment)
4. [Creative](#creative)
5. [Targeting](#targeting)
6. [Data Extraction](#data-extraction)

## General

General Configuration is still pretty Facebook specific. This is used to setup
the study and "glue" together all the various other configurations. 

### Fields

- `name (required)`: a unique name of the study used as an identifier
- `objective (required)`:
- `optimization_goal (required)`: What are we trying to optimize for? Currently
    Supports [`Link Clicks`]
- `destination_type (required)`: The type of destination that we are routing
    recruited people to [`Messenger`, `Web`, `App`]
- `page_id (required)`: The identifier for the Facebook page that the study
    will be run from
- `instagram_id (optional)`: The identifier of the Instagram account to use to
    target recruits
- `min_budget (required)`: The minimum budget for the campaign
- `opt_window (required)`:
- `ad_account (required)`: The Ad's account to use to setup the ads used to
    recruit
- `extra_metadata (required)`:

## Destination

### Fields

## Recruitment

### Fields

## Creative

### Fields

## Targeting

### Fields

## Data Extraction

### Fields
