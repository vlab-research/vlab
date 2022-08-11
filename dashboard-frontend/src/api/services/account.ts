import { SecretAccountResource, TokenAccountResource } from '../../types/account';
const PATH = '/account';

export const connectAccount = async function (
  authType: string,
  data: TokenAccountResource | SecretAccountResource
) {
  try {
    console.log('token ->', authType, data, PATH);
    // const res = await axios.post(`${PATH}/details`, { authType, data });
    // return res.data;
    return {
      error: false,
    }
  } catch (error: any) {
    if (error.response && error.response.data.status) {
      // req success
      return { ...error.response.data, error: true };
    } else {
      // req no success
      return { error: true, msg: "can't make request" };
    }
  }
};

export const getDetails = async function () {
  // return await axios.get(`${PATH}/details`, { }).then(res => res.data);
  return 
};
