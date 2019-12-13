# Copyright 2019-2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from unittest.mock import Mock, patch

import braket.aws.aws_qpu  # noqa F401
import pytest
from braket.aws import AwsQpu, AwsQpuArns
from braket.circuits import Circuit
from common_test_utils import MockDevices


@pytest.fixture
def qpu(aws_session):
    def _qpu(arn):
        aws_session.get_qpu_metadata.return_value = MockDevices.MOCK_RIGETTI_QPU_1
        return AwsQpu(arn, aws_session)

    return _qpu


@pytest.fixture
def s3_destination_folder():
    return ("bucket-foo", "key-bar")


@pytest.fixture
def circuit():
    return Circuit().h(0)


@pytest.fixture
def boto_session():
    _boto_session = Mock()
    _boto_session.region_name = AwsQpu.QPU_REGIONS[AwsQpuArns.RIGETTI][0]
    return _boto_session


@pytest.fixture
def aws_session():
    _boto_session = Mock()
    _boto_session.region_name = AwsQpu.QPU_REGIONS[AwsQpuArns.RIGETTI][0]
    _aws_session = Mock()
    _aws_session.boto_session = _boto_session
    return _aws_session


@pytest.mark.xfail(raises=ValueError)
def test_unknown_qpu_arn(aws_session):
    AwsQpu("foobar", aws_session)


def test_aws_session_in_qpu_region(aws_session):
    arn = AwsQpuArns.RIGETTI
    aws_session.boto_session.region_name = AwsQpu.QPU_REGIONS[arn][0]
    aws_session.get_qpu_metadata.return_value = MockDevices.MOCK_RIGETTI_QPU_1
    AwsQpu(arn, aws_session)

    aws_session.get_qpu_metadata.assert_called_with(arn)


@patch("braket.aws.aws_qpu.AwsSession")
@patch("boto3.Session")
def test_aws_session_in_another_qpu_region(
    boto_session_init, aws_session_init, boto_session, aws_session
):
    arn = AwsQpuArns.RIGETTI
    region = AwsQpu.QPU_REGIONS.get(arn)[0]

    boto_session_init.return_value = boto_session
    aws_session_init.return_value = aws_session
    aws_session.get_qpu_metadata.return_value = MockDevices.MOCK_RIGETTI_QPU_1

    creds = Mock()
    creds.access_key = "access key"
    creds.secret_key = "secret key"
    creds.token = "token"

    different_region_aws_session = Mock()
    different_region_aws_session.boto_session.get_credentials.return_value = creds
    different_region_aws_session.boto_session.profile_name = "profile name"
    different_region_aws_session.boto_session.region_name = "foobar"

    AwsQpu(arn, different_region_aws_session)

    # assert creds, profile, and region were correctly supplied
    boto_session_init.assert_called_with(
        aws_access_key_id=creds.access_key,
        aws_secret_access_key=creds.secret_key,
        aws_session_token=creds.token,
        profile_name=different_region_aws_session.boto_session.profile_name,
        region_name=region,
    )

    # assert supplied session, different_region_aws_session, was replaced
    aws_session.get_qpu_metadata.assert_called_with(arn)


@patch("braket.aws.aws_qpu.AwsSession")
@patch("boto3.Session")
def test_no_aws_session_supplied(boto_session_init, aws_session_init, boto_session, aws_session):
    arn = AwsQpuArns.RIGETTI
    region = AwsQpu.QPU_REGIONS.get(arn)[0]

    boto_session_init.return_value = boto_session
    aws_session_init.return_value = aws_session
    aws_session.get_qpu_metadata.return_value = MockDevices.MOCK_RIGETTI_QPU_1

    AwsQpu(arn)

    boto_session_init.assert_called_with(region_name=region)
    aws_session.get_qpu_metadata.assert_called_with(arn)


def test_qpu_refresh_metadata_success(aws_session):
    aws_session.get_qpu_metadata.return_value = MockDevices.MOCK_RIGETTI_QPU_1
    qpu = AwsQpu(AwsQpuArns.RIGETTI, aws_session)
    assert qpu.arn == MockDevices.MOCK_RIGETTI_QPU_1.get("arn")
    assert qpu.name == MockDevices.MOCK_RIGETTI_QPU_1.get("name")
    assert qpu.qubit_count == MockDevices.MOCK_RIGETTI_QPU_1.get("qubitCount")
    assert qpu.connectivity_graph == MockDevices.MOCK_RIGETTI_QPU_1.get("connectivity").get(
        "connectivityGraph"
    )
    assert qpu.supported_quantum_operations == MockDevices.MOCK_RIGETTI_QPU_1.get(
        "supportedQuantumOperations"
    )
    assert qpu.status == MockDevices.MOCK_RIGETTI_QPU_1.get("status")
    assert qpu.status_reason is None

    # describe_qpus now returns new metadata
    aws_session.get_qpu_metadata.return_value = MockDevices.MOCK_RIGETTI_QPU_2
    qpu.refresh_metadata()
    assert qpu.arn == MockDevices.MOCK_RIGETTI_QPU_2.get("arn")
    assert qpu.name == MockDevices.MOCK_RIGETTI_QPU_2.get("name")
    assert qpu.qubit_count == MockDevices.MOCK_RIGETTI_QPU_2.get("qubitCount")
    assert qpu.connectivity_graph == MockDevices.MOCK_RIGETTI_QPU_2.get("connectivity").get(
        "connectivityGraph"
    )
    assert qpu.supported_quantum_operations == MockDevices.MOCK_RIGETTI_QPU_2.get(
        "supportedQuantumOperations"
    )
    assert qpu.status == MockDevices.MOCK_RIGETTI_QPU_2.get("status")
    assert qpu.status_reason == MockDevices.MOCK_RIGETTI_QPU_2.get("statusReason")


def test_qpu_refresh_metadata_error(aws_session):
    err_message = "nooo!"
    aws_session.get_qpu_metadata.side_effect = RuntimeError(err_message)
    with pytest.raises(RuntimeError) as excinfo:
        AwsQpu(AwsQpuArns.RIGETTI, aws_session)
    assert err_message in str(excinfo.value)


def test_equality(qpu, aws_session):
    qpu_1 = qpu(AwsQpuArns.RIGETTI)
    qpu_2 = qpu(AwsQpuArns.RIGETTI)
    aws_session.get_qpu_metadata.return_value = MockDevices.MOCK_IONQ_QPU
    aws_session.boto_session.region_name = AwsQpu.QPU_REGIONS[AwsQpuArns.IONQ][0]
    other_qpu = AwsQpu(AwsQpuArns.IONQ, aws_session)
    non_qpu = "HI"

    assert qpu_1 == qpu_2
    assert qpu_1 is not qpu_2
    assert qpu_1 != other_qpu
    assert qpu_1 != non_qpu


def test_repr(qpu):
    qpu = qpu(AwsQpuArns.RIGETTI)
    expected = "QPU('name': {}, 'arn': {})".format(qpu.name, qpu.arn)
    assert repr(qpu) == expected


@patch("braket.aws.aws_quantum_task.AwsQuantumTask.from_circuit")
def test_run_with_positional_args(aws_quantum_task_mock, qpu, circuit, s3_destination_folder):
    _run_and_assert(aws_quantum_task_mock, qpu, [circuit, s3_destination_folder], {})


@patch("braket.aws.aws_quantum_task.AwsQuantumTask.from_circuit")
def test_run_with_kwargs(aws_quantum_task_mock, qpu, circuit, s3_destination_folder):
    _run_and_assert(
        aws_quantum_task_mock,
        qpu,
        [],
        {"circuit": circuit, "s3_destination_folder": s3_destination_folder},
    )


@patch("braket.aws.aws_quantum_task.AwsQuantumTask.from_circuit")
def test_run_with_positional_args_and_kwargs(
    aws_quantum_task_mock, qpu, circuit, s3_destination_folder
):
    _run_and_assert(aws_quantum_task_mock, qpu, [circuit, s3_destination_folder], {"shots": 100})


def _run_and_assert(aws_quantum_task_mock, qpu, run_args, run_kwargs):
    task_mock = Mock()
    aws_quantum_task_mock.return_value = task_mock

    qpu = qpu(AwsQpuArns.RIGETTI)
    task = qpu.run(*run_args, **run_kwargs)
    assert task == task_mock
    aws_quantum_task_mock.assert_called_with(qpu._aws_session, qpu.arn, *run_args, **run_kwargs)
