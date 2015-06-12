"""
HeapSet class defines an object that consists of a Fibonacci heap as well as a set.
fibonacc_heap_mod permits duplicate entries while we need elements to be unique.

Keeping a set alongside allows O(1) lookup to verify membership and prevent duplicate
insertion into th heap. The only other operation on the set is deletion which is also O(1).
"""
from fibonacci_heap_mod import Fibonacci_heap


class HeapSet(object):
    """
    fibonacci_heap + set = HeapSet
    includes a priority order for heap insertion and lookup
    """
    def __init__(self, priority):
        self.heap = Fibonacci_heap()
        self.set = set({})
        self.priority = priority

    def __repr__(self):
        return '<HeapSet({})>'.format(self.set)

    def add(self, element):
        """
        Add element only if it isn't already in.
        """
        if element not in self.set:
            self.set.add(element)
            self.heap.enqueue(element, self.priority(element))

    def pop(self):
        """
        Remove the min element
        """
        elem = self.heap.dequeue_min().get_value()
        self.set.remove(elem)
        return elem
