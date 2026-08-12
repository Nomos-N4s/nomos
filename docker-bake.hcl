variable "IMAGE" {
  default = "ghcr.io/nomos-n4s/nomos"
}

variable "VERSION" {
  default = "v0.0.0"
}

variable "PRERELEASE" {
  default = "true"
}

variable "REVISION" {
  default = ""
}

variable "CREATED" {
  default = ""
}

variable "RUN_TESTS" {
  default = "0"
}

function "oci_labels" {
  params = [version]
  result = {
    "org.opencontainers.image.title"       = "Nomos",
    "org.opencontainers.image.description" = "A formal framework for self-governing AI",
    "org.opencontainers.image.source"      = "https://github.com/Nomos-N4s/nomos",
    "org.opencontainers.image.version"     = version,
    "org.opencontainers.image.revision"    = REVISION,
    "org.opencontainers.image.licenses"    = "Apache-2.0",
    "org.opencontainers.image.created"     = CREATED,
  }
}

group "default" {
  targets = ["base", "with-rl"]
}

target "base" {
  target     = "base"
  platforms  = ["linux/amd64"]
  args       = { RUN_TESTS = RUN_TESTS }
  cache-from = ["type=gha,scope=nomos-base"]
  cache-to   = ["type=gha,mode=max,scope=nomos-base"]
  tags = concat(
    ["${IMAGE}:${VERSION}"],
    PRERELEASE == "false" ? ["${IMAGE}:latest"] : [],
  )
  labels = oci_labels(VERSION)
}

target "with-rl" {
  target     = "with-rl"
  platforms  = ["linux/amd64"]
  args       = { RUN_TESTS = RUN_TESTS }
  cache-from = ["type=gha,scope=nomos-with-rl"]
  cache-to   = ["type=gha,mode=max,scope=nomos-with-rl"]
  tags       = ["${IMAGE}:with-rl"]
  labels     = oci_labels(VERSION)
}
