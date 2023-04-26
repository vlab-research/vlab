import { translateField, getInitialValue } from './translateField';
import Select from '../pages/NewStudyPage/components/form/inputs/Select';
import Text from '../pages/NewStudyPage/components/form/inputs/Text';
import Button from '../pages/NewStudyPage/components/form/inputs/Button';
import text from '../../mocks/components/text';
import select from '../../mocks/components/select';
import number from '../../mocks/components/number';
import button from '../../mocks/components/button';
import Fieldset from '../pages/NewStudyPage/components/form/Fieldset';
import app from '../pages/StudyConfPage/confs/destinations/app';
import messenger from '../pages/StudyConfPage/confs/destinations/messenger';
import web from '../pages/StudyConfPage/confs/destinations/web';

describe('translateField', () => {
  it('given a field it returns a new object configured for rendering a form', () => {
    const textExpectation = {
      id: 'foo',
      name: 'foo',
      type: 'text',
      component: Text,
      label: 'Foo',
      helper_text: 'foo...',
      options: undefined,
      value: '',
      conf: null,
    };

    const res = translateField(text);
    expect(res).toStrictEqual(textExpectation);

    const selectExpectation = {
      id: 'bar',
      name: 'bar',
      type: 'select',
      component: Select,
      label: 'Bar',
      helper_text: undefined,
      options: [
        {
          name: 'foo',
          label: 'Foo',
        },
        {
          name: 'bar',
          label: 'Bar',
        },
        {
          name: 'baz',
          label: 'Baz',
        },
      ],
      value: 'foo',
      conf: null,
    };

    const res2 = translateField(select);
    expect(res2).toStrictEqual(selectExpectation);

    const numberExpectation = {
      id: 'baz',
      name: 'baz',
      type: 'number',
      component: Text,
      label: 'Baz',
      helper_text: 'baz...',
      options: undefined,
      value: 1,
      conf: null,
    };
    const res3 = translateField(number);
    expect(res3).toStrictEqual(numberExpectation);

    const buttonExpectation = {
      id: 'foo',
      name: 'foo',
      type: 'button',
      component: Button,
      label: 'Foo',
      helper_text: undefined,
      options: undefined,
      value: '',
      conf: null,
    };
    const res4 = translateField(button);
    expect(res4).toStrictEqual(buttonExpectation);

    const fieldsetExpectation = {
      id: 'destination_create',
      name: 'destination_create',
      type: 'fieldset',
      component: Fieldset,
      label: 'Create a destination',
      helper_text: undefined,
      options: undefined,
      value: [],
      conf: {
        type: 'confSelect',
        title: 'Destinations',
        description:
          'Every study needs a destination, where do the recruitment ads send the users?',
        fields: [
          {
            name: 'destination_type',
            type: 'select',
            label: 'Select a destination type',
            options: [
              {
                name: 'messenger',
                label: 'Messenger',
              },
              {
                name: 'web',
                label: 'Web',
              },
              {
                name: 'app',
                label: 'App',
              },
            ],
          },
          {
            name: 'initial_shortcode',
            type: 'text',
            label: 'Initial shortcode',
            helper_text: 'E.g 12345',
          },
          {
            name: 'destination_name',
            type: 'text',
            label: 'Destination name',
            helper_text: 'E.g example-fly-1',
          },
        ],
      },
    };

    const fieldset = {
      id: 'destination_create',
      name: 'destination_create',
      type: 'fieldset',
      component: Fieldset,
      label: 'Create a destination',
      helper_text: undefined,
      options: undefined,
      value: [],
      conf: {
        type: 'confSelect',
        title: 'Destinations',
        description:
          'Every study needs a destination, where do the recruitment ads send the users?',
        fields: [
          {
            name: 'destination_type',
            type: 'select',
            label: 'Select a destination type',
            options: [messenger, web, app],
          },
          {
            name: 'initial_shortcode',
            type: 'text',
            label: 'Initial shortcode',
            helper_text: 'E.g 12345',
          },
          {
            name: 'destination_name',
            type: 'text',
            label: 'Destination name',
            helper_text: 'E.g example-fly-1',
          },
        ],
      },
    };

    const res5 = translateField(fieldset);

    // expect(res5).toStrictEqual(fieldsetExpectation);
  });
});

describe('getInitialValue', () => {
  it('given a field it returns an initial value based on its type', () => {
    let res = getInitialValue(text);
    expect(res).toStrictEqual('');

    res = getInitialValue(number);
    expect(res).toStrictEqual(1);

    res = getInitialValue(select);
    expect(res).toStrictEqual('foo');
  });
});
