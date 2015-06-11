from fibonacci_heap_mod import Fibonacci_heap


class HeapSet(object):
    def __init__(self, priority):
        self.heap = Fibonacci_heap()
        self.set = set({})
        self.priority = priority

    def __repr__(self):
        return '<HeapSet({})>'.format(self.set)

    def add(self, element):
        if element not in self.set:
            self.set.add(element)
            self.heap.enqueue(element, self.priority(element))

    def pop(self):
        elem = self.heap.dequeue_min().get_value()
        self.set.remove(elem)
        return elem