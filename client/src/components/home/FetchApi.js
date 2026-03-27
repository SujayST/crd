import axios from "axios";
const apiURL = process.env.REACT_APP_API_URL;

const BearerToken = () =>
  localStorage.getItem("jwt")
    ? JSON.parse(localStorage.getItem("jwt")).token
    : false;
const Headers = () => {
  return {
    headers: {
      token: `Bearer ${BearerToken()}`,
    },
  };
};

export const getAllCategory = async () => {
  try {
    let res = await axios.get(`${apiURL}/api/category/all-category`, { withCredentials: true });
    return res.data;
  } catch (error) {
    console.log(error);
  }
};
export const getVectorStores = async (username) => {
  try {
    let res = await axios.get(`${apiURL}/api/vector_stores?username=${username}`);
    console.log("res: ", res);
    return res.data.vector_stores;
  } catch (error) {
    console.log(error);
  }
};
