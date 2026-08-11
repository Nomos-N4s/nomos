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

function "oci_labels" {
  params = [version]
  result = {
    "org.opencontainers.image.title"       = "Nomos",
    "org.opencontainers.image.description" = "A formal framework for self-governing AI",
    "org.opencontainers.image.source"      = "https://github.com/Nomos-N4s/nomos",
    "org.opencontainers.image.version"     = version,
    "org.opencontainers.image.revision"    = REVISION,
    "org.opencontainers.image.licenses"    = "Apache-2.0",
    "org.opencontainers.image.created"     = timestamp(),
  }
}

group "default" {
  targets = ["base", "with-rl"]
}

target "base" {
  target    = "base"
  platforms = ["linux/amd64", "linux/arm64"]
  tags = concat(
    ["${IMAGE}:${VERSION}"],
    PRERELEASE == "false" ? ["${IMAGE}:latest"] : [],
  )
  labels = oci_labels(VERSION)
}

target "with-rl" {
  target    = "with-rl"
  platforms = ["linux/amd64", "linux/arm64"]
  tags      = ["${IMAGE}:with-rl"]
  labels    = oci_labels(VERSION)
}