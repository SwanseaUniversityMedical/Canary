import { RuleConfigSeverity } from '@commitlint/types';

export default {
  extends: ['@commitlint/config-conventional'],
  parserPreset: 'conventional-changelog-conventionalcommits',
  rules: {
    'scope-enum': [RuleConfigSeverity.Error, 'always', [
        '',
        'deps',
        'canary-container',
        'canary-chart',
        'canary-crds-chart'
    ]],
    'subject-case': [RuleConfigSeverity.Error, 'never', []],
  }
};
