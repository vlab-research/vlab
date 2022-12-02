import { formBuilder } from './formBuilder';
import textField from '../../mocks/text.json';
import selectField from '../../mocks/select.json';
import SelectInput from '../pages/NewStudyPage/inputs/Select';
import TextInput from '../pages/NewStudyPage/inputs/Text';

describe('formBuilder', () => {
  it('takes an object and returns a new object configured for creating a form', () => {
    const expectation = {
      id: 'foo_bar',
      name: 'foo_bar',
      type: 'text',
      component: TextInput,
      label: 'Foo',
      helperText: 'foo',
      options: undefined,
    };

    const res = formBuilder(textField);
    expect(res).toStrictEqual(expectation);

    const expectation2 = {
      id: 'foo_bar',
      name: 'foo_bar',
      type: 'select',
      component: SelectInput,
      label: 'Foo',
      helperText: undefined,
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
    };

    const res2 = formBuilder(selectField);
    expect(res2).toStrictEqual(expectation2);
  });
});
