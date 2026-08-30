import http from 'k6/http';
import { check, sleep } from 'k6';

const TARGET_URL = __ENV.TARGET_URL;

// Much safer levels based on what we learned from Experiment 2.
const LOW = 1;
const MEDIUM = 3;
const HIGH = 6;
const SPIKE = 12;

export const options = {
    stages: [

        // ==================================================
        // HOUR 1 — Low → gradual ramp → high → recovery
        // ==================================================
        { duration: '10m', target: LOW },
        { duration: '20m', target: MEDIUM },
        { duration: '10m', target: MEDIUM },
        { duration: '5m', target: HIGH },
        { duration: '10m', target: HIGH },
        { duration: '5m', target: LOW },


        // ==================================================
        // HOUR 2 — Oscillating / changing workload
        // ==================================================
        { duration: '10m', target: LOW },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: HIGH },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: HIGH },
        { duration: '5m', target: LOW },
        { duration: '5m', target: HIGH },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: LOW },
        { duration: '5m', target: SPIKE },
        { duration: '5m', target: LOW },


        // ==================================================
        // HOUR 3 — Sudden spike + controlled recovery
        // ==================================================
        { duration: '10m', target: LOW },
        { duration: '10m', target: MEDIUM },
        { duration: '5m', target: MEDIUM },
        { duration: '2m', target: SPIKE },
        { duration: '5m', target: SPIKE },
        { duration: '8m', target: HIGH },
        { duration: '10m', target: HIGH },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: LOW },


        // ==================================================
        // HOUR 4 — Long gradual ramp and fall
        // ==================================================
        { duration: '15m', target: LOW },
        { duration: '20m', target: HIGH },
        { duration: '10m', target: HIGH },
        { duration: '10m', target: MEDIUM },
        { duration: '5m', target: LOW },


        // ==================================================
        // HOUR 5 — Bursty / semi-random behaviour
        // ==================================================
        { duration: '5m', target: LOW },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: HIGH },
        { duration: '5m', target: LOW },
        { duration: '5m', target: SPIKE },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: HIGH },
        { duration: '5m', target: LOW },
        { duration: '5m', target: SPIKE },
        { duration: '5m', target: HIGH },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: LOW },


        // ==================================================
        // HOUR 6 — Stable + ramp + spike sequence
        // ==================================================
        { duration: '10m', target: LOW },
        { duration: '15m', target: MEDIUM },
        { duration: '10m', target: MEDIUM },
        { duration: '5m', target: SPIKE },
        { duration: '5m', target: HIGH },
        { duration: '5m', target: SPIKE },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: LOW },


        // ==================================================
        // HOUR 7 — Repeated oscillations
        // ==================================================
        { duration: '10m', target: LOW },
        { duration: '5m', target: HIGH },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: HIGH },
        { duration: '5m', target: LOW },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: HIGH },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: LOW },
        { duration: '5m', target: SPIKE },
        { duration: '5m', target: LOW },


        // ==================================================
        // HOUR 8 — Slow growth → sustained load → drop
        // ==================================================
        { duration: '10m', target: LOW },
        { duration: '25m', target: HIGH },
        { duration: '10m', target: HIGH },
        { duration: '5m', target: SPIKE },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: LOW },


        // ==================================================
        // HOUR 9 — Mixed unpredictable-looking sequence
        // ==================================================
        { duration: '5m', target: LOW },
        { duration: '5m', target: HIGH },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: SPIKE },
        { duration: '5m', target: LOW },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: HIGH },
        { duration: '5m', target: LOW },
        { duration: '5m', target: SPIKE },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: HIGH },
        { duration: '5m', target: LOW },


        // ==================================================
        // HOUR 10 — Final representative cycle + recovery
        // ==================================================
        { duration: '10m', target: LOW },
        { duration: '15m', target: MEDIUM },
        { duration: '10m', target: HIGH },
        { duration: '5m', target: SPIKE },
        { duration: '5m', target: HIGH },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: LOW },

        // Final graceful ramp to zero load
        { duration: '5m', target: 0 },
    ],

    thresholds: {
        http_req_failed: ['rate<0.20'],
    },
};


export default function () {

    const response = http.get(TARGET_URL);

    check(response, {
        'HTTP response received':
            (r) => r.status >= 200 && r.status < 500,
    });

    sleep(1);
}