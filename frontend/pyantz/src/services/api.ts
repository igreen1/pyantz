import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL, // Use the environment variable
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;