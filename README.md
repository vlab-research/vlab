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


### General

The "general" configuration consists of... General stuff?


### Destination

Every study needs a destination, where do the recruitment ads send the users? There are several types:

1. Web Destination. Used to send to a website or web survey platform. This creates "web destination" ads in Facebook.

2. Fly Messenger Survey Destination. This creates "Messenger ads" in Facebook for when you want the user to be directed to a Messenger bot.

3. App Destination. This creates "app download" ads in Facebook, for when you want the user to directly download an app from the ad.


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
