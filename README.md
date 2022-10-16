# Virtual Lab

Virtual Lab is a platform for running experiments easily, efficiently, and iteratively.

## Creating a Study

Creating a study consists of configuring a lot of different variables, separated into groups.

All studies require the following configurations:

1. General
2. Destination
3. Recruitment
4. Creative
5. Targeting
6. Data Extraction

### General

The "general" configuration consists of... General stuff?


### Destination

Every study needs a destination, where do the recruitment ads send the users? Destinations need to be connected to Virtual Lab so that, not only does it know where to send people who click on the recruitment ads, but also so that it knows how to collect the information about those who become study participants and knows how to optimize ads.

Towards that end, Virtual Lab supports a set a "destinations" and is written in such a way that it is easy to add a new destination. The following are currently supported along with their method of configuation:

1. Fly Messenger Survey Destination. This creates "Messenger ads" in Facebook for when you want the user to be directed to a Fly Messenger Survey. It requires the following parameters:
   - `initial_shortcode: str` The shortcode of the initial form users should be sent to.
   - `survey_name: str` The survey that contains all the forms with data of interest.

2. Typeform. Each Typeform destination needs the following parameters:
    - `form_id: str` The Form ID of the Typeform you wish to send users to.

3. Curious Learning Literacy Apps. Requires the following parameters:
   - `from: int` Starting timestamp for retrieving app events from Literacy Data API.
   - `app_id: str` The app ID for the Google Play store.
   - `facebook_app_id: str` he app ID for Facebook.
   - `deeplink_template: str`
   - `app_install_state: str`
   - `user_device: list[str]`
   - `user_os: list[str]`
   - `attribution_id: str`


### Recruitment

The "recruitment" configuration describes how/where recruitment will take place. Every study needs to recruit from somewhere.

There are currently 3 types of recruitments:

1. Simple.

2. Destination Experiment. Use this when you want to create a multi-arm randomized experiment (A/B test on Facebook) where some of your sample is sent to different "destinations".

3. Pipeline Experiment. In this design, we generate an A/B test on Facebook but instead of sending your sample to different destinations, we run the ads at different times (a pipeline experiment design). You can set up how long each arm runs, and how long they are offset from the start of the rpevious arm.


### Creative

Recruitment needs ads and ads need creative. Each creative consists of one of several fields:

[fields]

Each creative also needs to be linked to a particular "destination". If you only have one destination (simple recruitment or pipeline experiment), they will all link to the same destination. If you have multiple destinations (Destination Experiment), then you need to specify different creative for each destination.

### Targeting

Targeting describes the variables for stratification and the desired joint distribution of respondents.

1. Template Campaign Name. If you have created template ads to target certain variables, this is the name of the campaign that has those ads.

2. Distribution Variables. The variables that you are using for stratification.

3. Distribution. What proportion of people do you want in your final sample from each stratum?


### Data Extraction

It's important to extract some data that the optimization engine can use. For example: variables that are used in stratification. In order to do so you must define how to pull these variables out of the data stream from the destination.

Our data model is very simple. Each study has a set of "users", or study participants, and each user has a set of variables, represented as unique strings, and each variable has a value. Values are represented as pure JSON bytes, so they can be strings, numbers, booleans, arrays, objects, etc., anything that can be modelled as JSON.

All data from supported destinations is modelled as individual events, where each event is associated to a user and each event has a "variable" and "metadata". Therefore, all that's left is for you to identify how to extract variables and values that you want to model from the events and their metadata.

This can be thought of in three parts:

1. Identification. For each variable, what events are associated with it.

2. Extraction. Given the associated event, how to extract the value.

3. Aggregation. How to compose values across events to have one final value for each variable. You can choose from the following aggregation functions: max, min, last, first. For example, if your destination is an app, which is a game, you might want to extract the level achieved and aggregate it with "max". If your variable is a piece of metadata that shows up in every event, you can choose first or last. If your variable is an answer to a question, you might choose last, to pick the last answer the user gave.


Here's the documentation:
1. [Python classes](https://github.com/vlab-research/vlab/blob/spike-recruitment-data/adopt/adopt/study_conf.py#L24-L39)

2. [Go Types](https://github.com/vlab-research/vlab/blob/spike-recruitment-data/inference/swoosh/inference_data.go#L14-L31)
