#   Copyright (c) 2018 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import time
import unittest
from multiprocessing import Process
import signal

import numpy

import paddle.fluid as fluid
import paddle.fluid.layers as layers
from paddle.fluid.layers.io import ListenAndServ
from paddle.fluid.layers.io import Recv
from paddle.fluid.layers.io import Send
import paddle.fluid.layers.ops as ops


class TestProgram2Code(unittest.TestCase):
    def test_print(self):
        place = fluid.CPUPlace()
        self.init_serv(place)
        self.init_client(place, 9123)

    def init_serv(self, place):
        main = fluid.Program()

        with fluid.program_guard(main):
            serv = ListenAndServ("127.0.0.1:0", ["X"], optimizer_mode=False)
            with serv.do():
                out_var = main.global_block().create_var(
                    name="scale_0.tmp_0",
                    psersistable=True,
                    dtype="float32",
                    shape=[32, 32])
                x = layers.data(
                    shape=[32, 32],
                    dtype='float32',
                    name="X",
                    append_batch_size=False)
                fluid.initializer.Constant(value=1.0)(x, main.global_block())
                ops._scale(x=x, scale=10.0, out=out_var)

        print(main)

    def init_client(self, place, port):
        main = fluid.Program()
        with fluid.program_guard(main):
            x = layers.data(
                shape=[32, 32],
                dtype='float32',
                name='X',
                append_batch_size=False)
            fluid.initializer.Constant(value=2.3)(x, main.global_block())
            get_var = main.global_block().create_var(
                name="scale_0.tmp_0",  # server side var
                dtype="float32",
                persistable=False,
                shape=[32, 32])
            fluid.initializer.Constant(value=2.3)(get_var, main.global_block())
            Send("127.0.0.1:%d" % port, [x])
            o = Recv("127.0.0.1:%d" % port, [get_var])

        print(main)


class TestProgramToReadableCode(unittest.TestCase):
    def setUp(self):
        self.program = fluid.Program()
        self.block = self.program.current_block()
        self.var = self.block.create_var(
            name="X", shape=[-1, 23, 48], dtype='float32')
        self.param = self.block.create_parameter(
            name="W", shape=[23, 48], dtype='float32', trainable=True)
        self.op = self.block.append_op(
            type="abs", inputs={"X": [self.var]}, outputs={"Out": [self.var]})
        # add control flow op and sub block
        self.append_cond_op(self.program)

    def append_cond_op(self, program):
        def true_func():
            return layers.fill_constant(shape=[2, 3], dtype='int32', value=2)

        def false_func():
            return layers.fill_constant(shape=[3, 2], dtype='int32', value=-1)

        with fluid.program_guard(program):
            x = layers.fill_constant(shape=[1], dtype='float32', value=0.1)
            y = layers.fill_constant(shape=[1], dtype='float32', value=0.23)
            pred = layers.less_than(y, x)
            out = layers.cond(pred, true_func, false_func)

    def test_program_code(self):
        self.var._to_readable_code()
        self.param._to_readable_code()
        self.op._to_readable_code()
        self.block._to_readable_code()
        self.program._to_readable_code()

    def test_program_print(self):
        print(self.var)
        print(self.param)
        print(self.op)
        print(self.block)
        print(self.program)


if __name__ == "__main__":
    unittest.main()
