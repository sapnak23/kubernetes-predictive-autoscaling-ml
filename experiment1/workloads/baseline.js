import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 20 },
    { duration: '2m', target: 50 },
    { duration: '2m', target: 100 },
    { duration: '2m', target: 200 },
    { duration: '2m', target: 100 },
    { duration: '1m', target: 20 },
    { duration: '1m', target: 0 },
  ],

  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<2000'],
  },
};

export default function () {
  const appUrl = __ENV.APP_URL;

if (!appUrl) {
    throw new Error('APP_URL environment variable is required');
}

  const response = http.get(appUrl);

  check(response, {
    'HTTP status is 200': (res) => res.status === 200,
    'response contains OK': (res) => res.body.includes('OK'),
  });

  sleep(0.1);
}