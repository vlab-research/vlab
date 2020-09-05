package main

import (
	"time"
	"log"
	"sync"
	"github.com/confluentinc/confluent-kafka-go/kafka"
)

type ConsumerInterface interface {
	ReadMessage (time.Duration) (*kafka.Message, error)
	Commit () ([]kafka.TopicPartition, error)
}

type KafkaConsumer struct {
	Consumer ConsumerInterface
	timeout time.Duration
	batchSize int
	chunkSize int
}

func NewKafkaConsumer(topic string, brokers string, group string, timeout time.Duration, batchSize int, chunkSize int) KafkaConsumer {
	c, err := kafka.NewConsumer(&kafka.ConfigMap{
		"bootstrap.servers": brokers,
		"group.id":          group,
		"auto.offset.reset": "earliest",
		"enable.auto.commit": "false",
		"max.poll.interval.ms": "300000",
	})

	if err != nil {
		panic(err)
	}

	c.SubscribeTopics([]string{topic}, nil)

	return KafkaConsumer{c, timeout, batchSize, chunkSize}
}



func merge(cs ...<-chan error) <-chan error {
    var wg sync.WaitGroup
    out := make(chan error)

    output := func(c <-chan error) {
        for n := range c {
            out <- n
        }
        wg.Done()
    }
    wg.Add(len(cs))
    for _, c := range cs {
        go output(c)
    }

    go func() {
        wg.Wait()
        close(out)
    }()
    return out
}


func chunk(ch chan *kafka.Message, size int) chan []*kafka.Message {
	var b []*kafka.Message
	out := make(chan []*kafka.Message)

	go func(){
		for v := range ch {
			b = append(b, v)
			if len(b) == size {
				out <- b
				b = make([]*kafka.Message, 0)
			}
		}
		// send the remaining partial buffer
		if len(b) > 0 {
			out <- b
		}
		close(out)
	}()

	return out
}

func chanWrap(fn SideEffectFn, m []*kafka.Message) <-chan error {
	errs := make(chan error)
	go func() {
		defer close(errs)
		err := fn(m)
		if err != nil {
			errs <- err
		}
	}()

	return errs
}

type SideEffectFn func([]*kafka.Message) error

func process (messages chan []*kafka.Message, fn SideEffectFn) <-chan error {
	chans := [] <-chan error{}
	for m := range messages {
		chans = append(chans, chanWrap(fn, m))
	}
	return merge(chans...)
}
 
func (consumer KafkaConsumer) SideEffect (fn SideEffectFn, errs chan error) {
	messages := consumer.Consume(errs)

	// block until finished processing
	// and all errors are checked
	perrs := process(messages, fn)
	for err := range perrs {
		errs <- err
	}

	// commit!
	_, err := consumer.Consumer.Commit()
	if err != nil {
		if e, ok := err.(kafka.Error); ok && e.Code() == kafka.ErrNoOffset {
			log.Print("Finished batch but committing 0 messages")
		} else {
			errs <- err
		}
	}
}


func (consumer KafkaConsumer) Consume (errs chan error) chan []*kafka.Message {
	return chunk(consumer.consumeStream(errs), consumer.chunkSize)
}


func (consumer KafkaConsumer) consumeStream (errs chan error) chan *kafka.Message {
	messages := make(chan *kafka.Message)
	c := consumer.Consumer

	// runs until n messages consumed
	go func() {
		defer close(messages)
		count := 0
		for i := 1; i <= consumer.batchSize; i++ {

			msg, err := c.ReadMessage(consumer.timeout)

			if err != nil {
				if e, ok := err.(kafka.Error); ok && e.Code() == kafka.ErrTimedOut {
					break
				}
				errs <- err
				break
			}

			messages <- msg
			count += 1
		}
		log.Printf("Consumed %v messages as batch from Kafka", count)
	}()

	return messages
}
