# Versioning a public API
<!-- stay:uUSVRylW hash=sha256:b290bb08b159 -->

Once an API has external consumers you no longer control, every change risks breaking
someone. Versioning is the contract that lets a service evolve without silently breaking
the clients that depend on it. The goal is not to avoid change, it is to make change
predictable.
<!-- stay:I01sCOwp hash=sha256:be1fa5abcc04 -->

## Backward-compatible changes
<!-- stay:QlXTvDMq hash=sha256:2fa9ed2f37ce -->

Many changes are safe and need no new version. Adding a new endpoint, adding an optional
field to a request, or adding a field to a response are all additive: an old client that
ignores the new field keeps working. The discipline is to treat unknown fields as
tolerable on both sides, so that adding one never breaks a careful consumer.
<!-- stay:tAHc2iI9 hash=sha256:31ddb1ce82ed -->

Breaking changes are different. Removing a field, renaming one, changing a type, or
making an optional field required all break clients that relied on the old shape. These
are the changes that require a version boundary.
<!-- stay:j3X6Ybiz hash=sha256:bdaceac4de04 -->

## URL versioning versus header versioning
<!-- stay:VK1mH5L3 hash=sha256:46f32e85bad0 -->

The most visible scheme puts the version in the URL path, such as /v1/orders and
/v2/orders. It is obvious, easy to route, and easy to test from a browser or a curl
command. The cost is that the version leaks into every link and every client, and a
major bump duplicates a lot of surface area.
<!-- stay:zvdSUVoC hash=sha256:762cd36c9be8 -->

Header versioning keeps the URL stable and selects the version through a request header
or a media type. It is cleaner in theory and keeps resource URLs canonical, but it is
invisible in a browser and easy for a client to forget, which is why many teams stay
with URL versioning despite its bluntness.
<!-- stay:5MAx9Zyd hash=sha256:7291bd75953f -->

## Deprecation
<!-- stay:BXJzMyNl hash=sha256:de9cfde469d6 -->

A version is only half the contract; the other half is how you retire one. A responsible
deprecation announces the date, returns a Deprecation header on the old version so
clients can detect it programmatically, and keeps the old version running long enough for
consumers to migrate. Cutting off a version without warning is the fastest way to lose
the trust that made the API worth integrating with.
<!-- stay:7gErHCru hash=sha256:93eeefb7cd4e -->

Keep a changelog that records every version and what changed in it. Consumers plan their
upgrades from that document, and a clear history is the difference between a smooth
migration and a flood of support tickets.
<!-- stay:PO0nm6Px hash=sha256:5647496f7018 -->
