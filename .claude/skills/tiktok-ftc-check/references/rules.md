# The rules this check applies

Each rule has an id. Findings cite the id, the source and a short quote. Sources were fetched on **2026-10-28**
(`scripts/rules.py status`). Firecrawl doesn't serve TikTok's Community Guidelines pages, so the quotes marked **(CG)**
were read with a web fetch, a summary that quotes passages, not a full copy. Check their exact wording on the page
before quoting them to a client. Everything else is from the full pages in the local cache (`rules.py search`).

This is a checklist for content, not legal advice. A campaign that is ❌ on any rule needs the brand's lawyer, not a
workaround.

## D: Disclosure (the post says it's paid)

**D1. TikTok's content disclosure setting is on.** Every post promoting a brand, product or service, including
paid clipping, turns on the setting, which labels it *Paid partnership*.
- TikTok Support, [Promoting a brand, product, or service](https://support.tiktok.com/en/business-and-creator/creator-and-business-accounts/promoting-a-brand-product-or-service):
  "When posting content that promotes a brand, product, or service on TikTok, you must turn on the content disclosure
  setting." "If you don't display the proper disclosure, we may remove or restrict your posts."
- **(CG)** [Regulated Goods and Commercial Activities](https://www.tiktok.com/community-guidelines/en/regulated-commercial-activities):
  "If you're posting commercial content on TikTok, you must clearly disclose it using the content disclosure setting."
  Repeated failures can lead to posting restrictions or a ban.

**D2. The disclosure is also in the post itself, where it can't be missed.** For a photo slideshow: "Ad" or
"Sponsored" on the first slide, and at the start of the caption.
- 16 CFR [§ 255.5](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-B/part-255#255.5): a connection between
  the endorser and the seller that "might materially affect the weight or credibility of the endorsement" and that the
  audience doesn't expect "must be disclosed clearly and conspicuously". Being paid per view is such a connection.
- FTC, [Disclosures 101 for Social Media Influencers](https://www.ftc.gov/business-guidance/resources/disclosures-101-social-media-influencers):
  "If your endorsement is in a picture … superimpose the disclosure over the picture." Disclosures "are likely to be
  missed if they appear only on an ABOUT ME or profile page, at the end of posts or videos, or anywhere that requires
  a person to click MORE." "advertisement," "ad," and "sponsored" are clear terms. "Don't assume that a platform's
  disclosure tool is good enough."

## T: Testimonials are real (the person exists, used it, and it happened)

**T1. No fake testimonials.** A post that viewers will read as someone's own experience ("my GLP-1 journey", "how I
lost 30 lbs") must come from a real person who had that experience. An AI-generated person, body or "progress"
presented as real is a fake testimonial.
- 16 CFR [§ 465.2(a)](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-D/part-465#465.2): it is unlawful
  for a business to "write, create, or sell a … consumer testimonial … that materially misrepresents … (1) That the
  reviewer or testimonialist exists; (2) That the reviewer or testimonialist used or otherwise had experience with the
  product …; or (3) The reviewer's or testimonialist's experience." § 465.2(b) covers disseminating one the business
  "knew or should have known" was fake. In force since October 21, 2024; the FTC can seek civil penalties.
- [§ 465.1(f)](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-D/part-465#465.1): a consumer testimonial
  includes "demonstrations, or depictions of the … likeness" that consumers are likely to believe reflect a
  consumer's experience. Photos count, not only words.

**T2. The endorser really uses it.** [§ 255.1(c)](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-B/part-255#255.1):
"When the advertisement represents that the endorser uses the endorsed product, the endorser must have been a bona
fide user of it at the time the endorsement was given." [§ 255.1(a)](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-B/part-255#255.1):
"Endorsements must reflect the honest opinions, findings, beliefs, or experience of the endorser."

**T3. People shown as real users are real users.** [§ 255.2(c)](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-B/part-255#255.2):
ads with what are represented as "actual consumers" should use actual consumers "or clearly and conspicuously
disclose that the persons in such advertisements are not actual consumers."

**T4. Everyone in the chain is liable.** [§ 255.1(d)–(f)](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-B/part-255#255.1):
the advertiser (the app), the endorser (the creator; "including when an endorser falsely represents that they
personally used a product") and "advertising agencies, public relations firms, review brokers … and other similar
intermediaries" (the campaign agency). Advertisers should give endorsers guidance on not misleading and on disclosing.

## R: Results and health claims

**R1. A before-and-after implies typical results.** [§ 255.2(b)](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-B/part-255#255.2):
an endorsement about a key attribute "will likely be interpreted as representing that the endorser's experience is
representative of what consumers will generally achieve." Its weight-loss example: "before" and "after" pictures with
"I lost 50 pounds in 6 months" convey typical results, so the ad needs the generally expected results, substantiated.
- FTC, [Health Products Compliance Guidance](https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance):
  "Testimonials that report results more dramatic than users can generally expect are likely to be deceptive.
  Moreover, attempts to disclaim dramatic results with statements like 'Results not typical' don't cure the
  deception."

**R2. Health claims need competent and reliable scientific evidence.** Same guidance: "claims about the health
benefits of a product must still meet the basic substantiation standard of 'competent and reliable scientific
evidence.'" A testimonial is not evidence. For a tracking app: say what it does (reminders, logs, charts), not that
it causes weight loss, unless the brand has studies that show it.

**R3. The product's own limits stand.** If the app store listing or label says "for tracking and educational
purposes only, not medical advice", the posts can't imply medical outcomes or advice.

## A: AI-generated content

**A1. Realistic AI images are labelled.** TikTok Support, [How is AI-generated content labeled](https://support.tiktok.com/en/using-tiktok/creating-videos/ai-generated-content):
"We also require creators to label all AI-generated content that contains realistic images, audio, and video."
**(CG)** [Integrity and Authenticity](https://www.tiktok.com/community-guidelines/en/integrity-authenticity): "we
require creators to label AI-generated or significantly edited content that shows realistic-looking scenes or
people … Unlabeled content may be removed, restricted, or labeled by our team."

**A2. Provenance isn't stripped to avoid the label.** TikTok auto-labels AI content that carries Content Credentials
(C2PA), and "once your content is labeled as AI-generated with an auto label, you won't be able to remove the label".
Removing a generator's watermark, SynthID or Content Credentials doesn't remove the duty to label (A1); doing it so
the label won't appear is evading it. A campaign step that does this is ❌, and the check never explains how to do it.

**A3. AI can't fake people.** Same support page: TikTok doesn't allow AI-generated content showing "the likeness of
young people under the age of 18, or the likeness of adult private figures used without their permission", or public
figures "making an endorsement, or being endorsed". "We take action on any content that violates our Community
Guidelines, regardless of whether it was altered with AI."

**A4. A label doesn't turn a fake testimonial into a real one.** An AI image labelled as AI can illustrate an idea
(a meal, a calendar, a mood). It can't stand in for a real person's results or journey; the story would still be a
fake testimonial (T1).

## I: Identity and accounts

**I1. Accounts are who they say they are.** **(CG)** [Integrity and Authenticity](https://www.tiktok.com/community-guidelines/en/integrity-authenticity):
prohibits "covert influence operations, impersonation, spam, fake reviews"; "You can have multiple accounts" but not
"to deceive others or break the rules"; the aim is content "shared by real people". A persona built to look like a
different person, or from a different country, to make the posts more credible is ❌. A creator making a new account
under their own identity is fine.

**I2. No fake signals of influence.** 16 CFR [§ 465.8](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-D/part-465#465.8):
no buying, selling or procuring fake "indicators of social media influence" for a commercial purpose; under
§ 465.1(h) these include indicators from "purported individual accounts not associated with a real individual".
**(CG)**: TikTok removes "fake likes, followers, or other inflated signals" and bans "automation tools, scripts, or
other tricks designed to bypass our systems."

**I3. Audience proof is real.** A campaign paying on Tier-1 share (US, UK, CA, AU) gets that audience honestly: by
where the creator and their followers really are. Faking location (VPNs, foreign SIMs, false profile details) to
qualify misrepresents the account to TikTok and to the brand.

## C: Categories TikTok restricts

**C1. Weight-loss and drug promotion.** TikTok's [Branded Content Policy](https://www.tiktok.com/legal/page/global/bc-policy/en)
prohibits branded content for "Weight loss products or services - Including weight loss clinics, weight loss and
weight management supplements …", "Drug-related products and services - Including … recreational and prescription
drugs", and "Pharmaceuticals, healthcare and medicine products, including: Any medical institutions, treatments or
devices, including nutritionists, online pharmacies and telehealth providers". Prescription-medicine branded content
is restricted to users over 18 in the market it was posted, where allowed at all.
**(CG)** [Mental and Behavioral Health](https://www.tiktok.com/community-guidelines/en/mental-behavioral-health): "We
also don't allow trading, marketing, or providing access to weight-related products … and services that include
exaggerated or harmful claims."
- What it means: a post can't promote a GLP-1 drug, where to get one, or a weight-loss service. A companion app for
  people already prescribed one sits close to the line. Whether TikTok treats it as a weight-loss service is TikTok's
  call, so it's ⚠️: say what the app does, keep the drug as context (the user's own prescription), and ask the brand
  whether TikTok has reviewed the category.

**C2. Body image and food.** Branded Content Policy: no branded content that will "promote or reinforce negative or
unhealthy body images, or exploit insecurities to conform to certain beauty ideals or standards" or "promote an
unhealthy relationship with food or exercise". **(CG)**: no content "that promotes disordered eating and risky
weight management behaviors."

## P: Platform quality

**P1. Original, not spam.** **(CG)** Integrity and Authenticity: spam and deceptive multiple accounts are prohibited.
Reposting someone else's slides or mass-posting near-identical slideshows across accounts is ❌. Each creator makes
their own posts.
