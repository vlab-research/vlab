# Sketch

**When creating a new study the user will be served different forms depending on the choices they make. Each form has an underlying config file which can be one of three types: configObject, configSelect or configList. This means that some forms are made up of one config whereas others can be made up of several.**

## Config-object

User lands on new study page and sees a form of type object. The form is simply the output of a `formBuilder()` function
which takes one argument – a single field object. It translates that field object into a new object with the additional properties required for creating a form.

```
const formBuilder = someField => {
    return {
        id: someField.name,
        name: someField.name,
        type: someField.type,
        component: component,
        label: someField.label,
        helper_text: someField.helper_text ?? someField.helper_text,
        options: someField.options ?? someField.options
    }
}
```

Field objects can be of any of the following types: `text`, `number`, `select`, and `list`. This is not to be confused with config `type`, which is what dictates the type of form displayed to the user.

So, if a config is of type `object` but it contains a `field` of type `select`, this just means that the user can select a single option from a set of dropdown options. Likewise, if the field is of type `list`, the user can simply select multiple options for a given input.

In contrast, a config of type `configSelect` or `configList` signals greater complexity which is explained below.

## configSelect

[simple, experiment, pipeline]

A `configSelect` form is where the user selects a nested form from a set of dropdown options. Think of it as a form within a form. Only one form can be selected which is what differentiates a `configSelecr` from a `configList`. To render each of the form options, the "parent" form makes use of the `fields` property within which there are `options`, one for each nested form.

So given an array of `options` for a config of type `configSelect` you might find the following structure.

```
const recruitment = {
  type: 'configSelect',
  title: 'Recruitment',
  description:
    'The "recruitment" configuration describes how/where recruitment will take place. Every study needs to recruit from somewhere.',
  fields: [
    {
      name: 'recruitment',
      type: 'select',
      label: 'Select a recruitment type',
      options: [
        recruitment_simple,
        recruitment_pipeline_experiment,
        recruitment_destination_experiment,
      ],
    },
  ],
};
```

If we look under the hood at the three recruitment types you will see that each option is simply a nested config that takes the same structure as its parent i.e `type`, `title`, `description`, and `fields`. The value of the `fields` will of course vary but the principle stucture of the config remains the same.

```
const recruitment = {
    type: 'configSelect',
    title: 'Recruitment',
    description: "recruitment.."
    fields: [
      name: 'recruitment',
      type: 'select',
      label: 'Select a recruitment type',
      options: [
        {
          name: 'simple',
          label: 'Simple',
          fields: [
            {
              name: 'ad_campaign_name',
              type: 'text',
              label: 'Ad Campaign Name',
              helper_text: 'E.g example-fly-conf',
            },
            {
              name: 'budget',
              type: 'number',
              label: 'Budget',
              helper_text: 'E.g 100',
            },
          ],
        },
        {
          name: 'pipeline',
          label: 'Pipeline',
          fields: [
            {
              name: 'ad_campaign_name_base',
              type: 'text',
              label: 'Ad Campaign Name Base',
              helper_text: 'E.g example-fly-conf',
            },
            {
              name: 'budget_per_arm',
              type: 'number',
              label: 'Budget per arm',
              helper_text: 'E.g 100',
            },
          ],
        },
          {
          name: 'destinations',
          label: 'Saved destinations',
          fields: [
            {
              name: 'ad_campaign_name_base',
              type: 'text',
              label: 'Ad Campaign Name Base',
              helper_text: 'E.g example-fly-conf',
            },
            {
              name: 'destinations',
              type: 'list',
              label: 'Saved destinations',
              options: mapDestinations(),
            },
          ],
        },
      ]
}
```

On submit of a `configSelect` form the user is displayed the nested form corresponding to their choice. So, if the user selects `pipeline`, the value stored from the `event.target` is sent to the top-level component where the code knows how to render the corresponding set of fields for that selection.

It's worth noting that within a config, a field may make reference to a value from another config.

Here's an example of a `configObject` that makes reference to a `configList`.

```
const recruitment_destination_experiment = {
  type: 'configObject',
  title: 'Recruitment destination',
  description:
    'Use this when you want to create a multi-arm randomized experiment (A/B test on Facebook) where some of your sample is sent to different "destinations".',
  fields: [
    {
      name: 'ad_campaign_name_base',
      type: 'text',
      label: 'Ad campaign name base',
      helper_text: 'E.g vlab-vaping-pilot-2',
    },
    {
      name: 'destinations',
      type: 'list',
      label: 'Saved destinations',
      options: mapDestinations(),
    },
  ],
};

```

Here we use a simple function to map over the list of destinations from the `destinations` config and for each one we return a `name` and a `label`.

```
import destinations from './destinations';

const { fields } = destinations;
const mapDestinations = () => {
  return fields.map(field =>
    field.options.map(option => {
      return { name: option.name, label: option.label };
    })
  );
};
```

## configList

[typeform, fly, curious_learning]

A `configList` form is where the user can select multiple forms from a set of options. Each form is built on top of any of the three config types, `configObject`, `configSelect`, and `configList`. Think of a `configList` as a union of multiple config types.

```
export const destinations = {
  type: 'config-multi',
  title: 'Destinations',
  description:
    'Every study needs a destination, where do the recruitment ads send the users?',
  fields: [
    {
      name: 'destinations',
      type: 'list',
      label: 'Add destination',
      options: [typeform, fly_messenger_destination, curious_learning],
    },
  ],
};
```

In this example we have a `destinations` config of type `configList` which indicates that we can select multiple options. Each option is a different config and has a unique key and set of fields. Like all other config types, the fields from a `configList` are passed to the `formBuilder` and from there we are able to access the sub-fields of any nested configs.

On submit of a `configList` choice, the user is displayed the nested form corresponding to their choice. So, if the user selects `Fly Messenger`, the value stored from the `event.target` is sent to the top-level component where the code knows how to render the corresponding set of fields for that selection.
