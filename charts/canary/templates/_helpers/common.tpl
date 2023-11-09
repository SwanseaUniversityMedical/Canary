{{/*
Define the image configs for containers
EXAMPLE USAGE: {{ include "image" (dict "image" .Values.canary.image) }}
*/}}
{{- define "canary.image" }}
image: {{ .image.repository }}:{{ .image.tag }}
imagePullPolicy: {{ .image.pullPolicy }}
securityContext:
  runAsUser: {{ .image.uid }}
  runAsGroup: {{ .image.gid }}
{{- end }}

{{/*
Construct the base name for all resources in this chart.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
*/}}
{{- define "canary.fullname" -}}
{{- printf "%s" .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Construct the `labels.app` for used by all resources in this chart.
*/}}
{{- define "canary.labels.app" -}}
{{- printf "%s" .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Construct the `labels.chart` for used by all resources in this chart.
*/}}
{{- define "canary.labels.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Define the nodeSelector for canary pods
EXAMPLE USAGE: {{ include "canary.nodeSelector" (dict "Release" .Release "Values" .Values "nodeSelector" $nodeSelector) }}
*/}}
{{- define "canary.podNodeSelector" }}
{{- .nodeSelector | default .Values.canary.defaultNodeSelector | toYaml }}
{{- end }}

{{/*
Define the Affinity for canary pods
EXAMPLE USAGE: {{ include "canary.podAffinity" (dict "Release" .Release "Values" .Values "affinity" $affinity) }}
*/}}
{{- define "canary.podAffinity" }}
{{- .affinity | default .Values.canary.defaultAffinity | toYaml }}
{{- end }}

{{/*
Define the Tolerations for canary pods
EXAMPLE USAGE: {{ include "canary.podTolerations" (dict "Release" .Release "Values" .Values "tolerations" $tolerations) }}
*/}}
{{- define "canary.podTolerations" }}
{{- .tolerations | default .Values.canary.defaultTolerations | toYaml }}
{{- end }}

{{/*
Define the PodSecurityContext for canary pods
EXAMPLE USAGE: {{ include "canary.podSecurityContext" (dict "Release" .Release "Values" .Values "securityContext" $securityContext) }}
*/}}
{{- define "canary.podSecurityContext" }}
{{- .securityContext | default .Values.canary.defaultSecurityContext | toYaml }}
{{- end }}

{{/*
The list of `volumeMounts` for canary pods
EXAMPLE USAGE: {{ include "canary.volumeMounts" (dict "Release" .Release "Values" .Values "extraVolumeMounts" $extraVolumeMounts) }}
*/}}
{{- define "canary.volumeMounts" }}
{{- /* user-defined (global) */ -}}
{{- if .Values.canary.extraVolumeMounts }}
{{ toYaml .Values.canary.extraVolumeMounts }}
{{- end }}

{{- /* user-defined */ -}}
{{- if .extraVolumeMounts }}
{{ toYaml .extraVolumeMounts }}
{{- end }}
{{- end }}

{{/*
The list of `volumes` for canary pods
EXAMPLE USAGE: {{ include "canary.volumes" (dict "Release" .Release "Values" .Values "extraVolumes" $extraVolumes) }}
*/}}
{{- define "canary.volumes" }}
{{- /* user-defined (global) */ -}}
{{- if .Values.canary.extraVolumes }}
{{ toYaml .Values.canary.extraVolumes }}
{{- end }}

{{- /* user-defined */ -}}
{{- if .extraVolumes }}
{{ toYaml .extraVolumes }}
{{- end }}
{{- end }}

{{/*
The list of `env` vars for canary pods
EXAMPLE USAGE: {{ include "canary.env" (dict "Release" .Release "Values" .Values "extraEnv" $extraEnv) }}
*/}}
{{- define "canary.env" }}
{{- /* user-defined (global) */ -}}
{{- if .Values.canary.extraEnv }}
{{ toYaml .Values.canary.extraEnv }}
{{- end }}

{{- /* user-defined */ -}}
{{- if .extraEnv }}
{{ toYaml .extraEnv }}
{{- end }}
{{- end }}

{{/*
The list of `envFrom` vars for canary pods
EXAMPLE USAGE: {{ include "canary.envFrom" (dict "Release" .Release "Values" .Values "extraEnvFrom" $extraEnvFrom) }}
*/}}
{{- define "canary.envFrom" }}
{{- /* user-defined (global) */ -}}
{{- if .Values.canary.extraEnvFrom }}
{{ toYaml .Values.canary.extraEnvFrom }}
{{- end }}

{{- /* user-defined */ -}}
{{- if .extraEnvFrom }}
{{ toYaml .extraEnvFrom }}
{{- end }}
{{- end }}

{{/*
The list of `containers` vars for canary pods
EXAMPLE USAGE: {{ include "canary.containers" (dict "Release" .Release "Values" .Values "extraContainers" $extraContainers) }}
*/}}
{{- define "canary.containers" }}
{{- /* user-defined (global) */ -}}
{{- if .Values.canary.extraContainers }}
{{ toYaml .Values.canary.extraContainers }}
{{- end }}

{{- /* user-defined */ -}}
{{- if .extraContainers }}
{{ toYaml .extraContainers }}
{{- end }}
{{- end }}
