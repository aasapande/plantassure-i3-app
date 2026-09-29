import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

export const http = axios.create({
  baseURL: API_BASE_URL,
  // Long enough for a sleeping free-tier server to wake up (about a minute).
  timeout: 70_000,
  headers: {
    Accept: 'application/json',
  },
});
