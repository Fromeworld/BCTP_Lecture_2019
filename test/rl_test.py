# https://towardsdatascience.com/how-to-install-openai-gym-in-a-windows-environment-338969e24d30

import gym

env = gym.make('CartPole-v0')
env.reset()

for _ in range(1000):
    env.render()
    env.step(env.action_space.sample())
    
env.close()