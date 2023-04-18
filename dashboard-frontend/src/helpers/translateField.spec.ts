import { translateField, getInitialValue } from './translateField';
import Select from '../pages/NewStudyPage/components/form/inputs/Select';
import Text from '../pages/NewStudyPage/components/form/inputs/Text';
import Button from '../pages/NewStudyPage/components/form/inputs/Button';
import text from '../../mocks/components/text';
import select from '../../mocks/components/select';
import number from '../../mocks/components/number';
import button from '../../mocks/components/button';

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
      conf: undefined,
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
      conf: undefined,
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
      conf: undefined,
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
      conf: undefined,
    };
    const res4 = translateField(button);
    expect(res4).toStrictEqual(buttonExpectation);
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
