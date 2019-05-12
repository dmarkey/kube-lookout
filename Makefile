IMAGE := davidjmarkey/kube-lookout

test:
	pytest

image:
	docker build -t $(IMAGE) .

push-image:
	@[ ! -z "$$TRAVIS_TAG" ] && echo "$$DOCKER_PASSWORD" | docker login -u "$$DOCKER_USERNAME" --password-stdin && docker tag $(IMAGE) $(IMAGE):$$TRAVIS_TAG && docker push $(IMAGE):$$TRAVIS_TAG || exit 0


.PHONY: image push-image test
