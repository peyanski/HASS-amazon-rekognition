"""AWS platform for image processing with AWS Rekognition."""
import asyncio
import base64
import json
import logging

import voluptuous as vol

from homeassistant.const import CONF_PLATFORM, CONF_NAME
from homeassistant.core import split_entity_id
from homeassistant.helpers.json import JSONEncoder

from homeassistant.components.image_processing import (
    PLATFORM_SCHEMA, ImageProcessingEntity, CONF_SOURCE, CONF_ENTITY_ID,
    CONF_NAME)

from .const import (
    CONF_ACCESS_KEY_ID,
    CONF_SECRET_ACCESS_KEY,
    CONF_REGION,
    CONF_SERVICE,
    CONF_TARGET,
)
from .notify import get_available_regions


_LOGGER = logging.getLogger(__name__)



def get_label_instances(response, target):
    """Get the number of instances of a target label."""
    for label in response['Labels']:
        if label['Name'] == target:
            return len(label['Instances'])
    return 0

def parse_labels(response):
    """Parse the API labels data, returning objects only."""
    return {label['Name']: round(label['Confidence'], 2) for label in response['Labels']}


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up Rekognition."""

    _LOGGER.error(
            "SETTING UP REKOGNITION",
        )

    aws_config = config.copy()

    import boto3
    aws_config = {
        CONF_REGION: aws_config[CONF_REGION],
        CONF_ACCESS_KEY_ID: aws_config[CONF_ACCESS_KEY_ID],
        CONF_SECRET_ACCESS_KEY: aws_config[CONF_SECRET_ACCESS_KEY],
        }

    client = boto3.client('rekognition', **aws_config) # Will not raise error.

    entities = []
    for camera in config[CONF_SOURCE]:
        entities.append(Rekognition(
            client,
            config.get(CONF_REGION),
            config.get(CONF_TARGET),
            camera[CONF_ENTITY_ID],
            camera.get(CONF_NAME),
        ))
    add_devices(entities)


class Rekognition(ImageProcessingEntity):
    """Perform object and label recognition."""

    def __init__(self, client, region, target, camera_entity, name=None):
        """Init with the client."""
        self._client = client
        self._region = region
        self._target = target
        if name:  # Since name is optional.
            self._name = name
        else:
            entity_name = split_entity_id(camera_entity)[1]
            self._name = "{} {} {}".format('rekognition', target, entity_name)
        self._camera_entity = camera_entity
        self._state = None  # The number of instances of interest
        self._labels = {} # The parsed label data

    def process_image(self, image):
        """Process an image."""
        self._state = None
        self._labels = {}
        response = self._client.detect_labels(Image={'Bytes': image})
        self._state = get_label_instances(response, self._target)
        self._labels = parse_labels(response)

    @property
    def camera_entity(self):
        """Return camera entity id from process pictures."""
        return self._camera_entity

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        attr = self._labels
        attr['target'] = self._target
        return attr

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name
