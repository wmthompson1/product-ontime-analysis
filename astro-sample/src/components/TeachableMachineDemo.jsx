import React, { useState, useEffect } from 'react';

const TeachableMachineDemo = () => {
  const [step, setStep] = useState(1);
  const [trainingData, setTrainingData] = useState([]);
  const [isTraining, setIsTraining] = useState(false);
  const [model, setModel] = useState(null);
  const [prediction, setPrediction] = useState(null);

  // Simulate the Teachable Machine workflow
  const steps = [
    { id: 1, title: "Gather Data", description: "Upload examples (like images, sounds, poses)" },
    { id: 2, title: "Train Model", description: "Let the machine learn patterns" },
    { id: 3, title: "Test & Use", description: "Get predictions on new data" }
  ];

  const frameworkComparison = {
    1: {
      teachable: "Upload training images by dragging and dropping",
      framework: "Define components with simple JSX syntax"
    },
    2: {
      teachable: "Click 'Train Model' and wait for automatic processing",
      framework: "Framework automatically handles DOM updates and state"
    },
    3: {
      teachable: "Test with new images to get instant predictions",
      framework: "User interactions trigger automatic UI updates"
    }
  };

  const addTrainingData = (category) => {
    const newData = {
      id: Date.now(),
      category,
      timestamp: new Date().toLocaleTimeString()
    };
    setTrainingData([...trainingData, newData]);
  };

  const trainModel = async () => {
    setIsTraining(true);
    // Simulate training time
    await new Promise(resolve => setTimeout(resolve, 2000));
    setModel({
      trained: true,
      accuracy: Math.random() * 20 + 80, // 80-100%
      categories: [...new Set(trainingData.map(d => d.category))]
    });
    setIsTraining(false);
  };

  const makePrediction = () => {
    if (model && model.categories.length > 0) {
      const randomCategory = model.categories[Math.floor(Math.random() * model.categories.length)];
      const confidence = Math.random() * 30 + 70; // 70-100%
      setPrediction({
        category: randomCategory,
        confidence: confidence.toFixed(1)
      });
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h3 className="text-2xl font-bold mb-6 text-center">Interactive Framework Demo</h3>
      
      {/* Step Navigation */}
      <div className="flex justify-center mb-8">
        {steps.map((s) => (
          <button
            key={s.id}
            onClick={() => setStep(s.id)}
            className={`mx-2 px-4 py-2 rounded-lg transition-colors ${
              step === s.id 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {s.id}. {s.title}
          </button>
        ))}
      </div>

      {/* Current Step Content */}
      <div className="min-h-96 border rounded-lg p-6 bg-gray-50">
        
        {/* Step 1: Gather Data */}
        {step === 1 && (
          <div>
            <h4 className="text-xl font-semibold mb-4">Step 1: Gather Training Data</h4>
            
            <div className="grid md:grid-cols-2 gap-6">
              {/* Teachable Machine Side */}
              <div className="bg-blue-50 p-4 rounded-lg">
                <h5 className="font-semibold text-blue-800 mb-3">Teachable Machine</h5>
                <p className="text-sm text-gray-600 mb-4">{frameworkComparison[1].teachable}</p>
                
                <div className="space-y-2">
                  <button 
                    onClick={() => addTrainingData('Cat')}
                    className="block w-full p-2 bg-blue-100 hover:bg-blue-200 rounded text-sm transition-colors"
                  >
                    + Add Cat Images
                  </button>
                  <button 
                    onClick={() => addTrainingData('Dog')}
                    className="block w-full p-2 bg-blue-100 hover:bg-blue-200 rounded text-sm transition-colors"
                  >
                    + Add Dog Images
                  </button>
                  <button 
                    onClick={() => addTrainingData('Bird')}
                    className="block w-full p-2 bg-blue-100 hover:bg-blue-200 rounded text-sm transition-colors"
                  >
                    + Add Bird Images
                  </button>
                </div>
              </div>

              {/* Framework Side */}
              <div className="bg-purple-50 p-4 rounded-lg">
                <h5 className="font-semibold text-purple-800 mb-3">JavaScript Framework</h5>
                <p className="text-sm text-gray-600 mb-4">{frameworkComparison[1].framework}</p>
                
                <pre className="text-xs bg-gray-800 text-green-400 p-3 rounded overflow-x-auto">
{`function DataUpload() {
  const [items, setItems] = useState([]);
  
  const addItem = (type) => {
    setItems([...items, {type, id: Date.now()}]);
  };
  
  return (
    <div>
      <button onClick={() => addItem('Cat')}>
        Add Cat
      </button>
    </div>
  );
}`}
                </pre>
              </div>
            </div>

            {/* Training Data Display */}
            {trainingData.length > 0 && (
              <div className="mt-6 p-4 bg-white rounded-lg border">
                <h5 className="font-semibold mb-3">Training Data Collected:</h5>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  {trainingData.map((data) => (
                    <div key={data.id} className="p-2 bg-gray-100 rounded text-sm text-center">
                      {data.category}
                      <br />
                      <span className="text-xs text-gray-500">{data.timestamp}</span>
                    </div>
                  ))}
                </div>
                <p className="text-sm text-gray-600 mt-2">
                  Total examples: {trainingData.length}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Step 2: Train Model */}
        {step === 2 && (
          <div>
            <h4 className="text-xl font-semibold mb-4">Step 2: Train the Model</h4>
            
            <div className="grid md:grid-cols-2 gap-6">
              {/* Teachable Machine Side */}
              <div className="bg-green-50 p-4 rounded-lg">
                <h5 className="font-semibold text-green-800 mb-3">Teachable Machine</h5>
                <p className="text-sm text-gray-600 mb-4">{frameworkComparison[2].teachable}</p>
                
                <button 
                  onClick={trainModel}
                  disabled={isTraining || trainingData.length === 0}
                  className={`w-full p-3 rounded font-semibold transition-colors ${
                    isTraining 
                      ? 'bg-yellow-200 text-yellow-800' 
                      : trainingData.length === 0
                      ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                      : 'bg-green-600 text-white hover:bg-green-700'
                  }`}
                >
                  {isTraining ? 'Training Model...' : 'Train Model'}
                </button>
                
                {isTraining && (
                  <div className="mt-3">
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div className="bg-green-600 h-2 rounded-full animate-pulse" style={{width: '60%'}}></div>
                    </div>
                    <p className="text-xs text-gray-600 mt-1">Learning patterns from your data...</p>
                  </div>
                )}
                
                {model && (
                  <div className="mt-4 p-3 bg-green-100 rounded">
                    <h6 className="font-semibold text-green-800">Model Trained!</h6>
                    <p className="text-sm text-green-700">
                      Accuracy: {model.accuracy.toFixed(1)}%
                      <br />
                      Categories: {model.categories.join(', ')}
                    </p>
                  </div>
                )}
              </div>

              {/* Framework Side */}
              <div className="bg-purple-50 p-4 rounded-lg">
                <h5 className="font-semibold text-purple-800 mb-3">JavaScript Framework</h5>
                <p className="text-sm text-gray-600 mb-4">{frameworkComparison[2].framework}</p>
                
                <pre className="text-xs bg-gray-800 text-green-400 p-3 rounded overflow-x-auto">
{`function ModelTrainer() {
  const [isTraining, setIsTraining] = useState(false);
  const [model, setModel] = useState(null);
  
  const train = async () => {
    setIsTraining(true);
    const result = await trainModel(data);
    setModel(result);
    setIsTraining(false);
  };
  
  return (
    <div>
      {isTraining && <Loading />}
      {model && <ModelResults model={model} />}
    </div>
  );
}`}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Test & Use */}
        {step === 3 && (
          <div>
            <h4 className="text-xl font-semibold mb-4">Step 3: Test & Use Your Model</h4>
            
            <div className="grid md:grid-cols-2 gap-6">
              {/* Teachable Machine Side */}
              <div className="bg-indigo-50 p-4 rounded-lg">
                <h5 className="font-semibold text-indigo-800 mb-3">Teachable Machine</h5>
                <p className="text-sm text-gray-600 mb-4">{frameworkComparison[3].teachable}</p>
                
                <button 
                  onClick={makePrediction}
                  disabled={!model}
                  className={`w-full p-3 rounded font-semibold transition-colors ${
                    !model 
                      ? 'bg-gray-200 text-gray-500 cursor-not-allowed' 
                      : 'bg-indigo-600 text-white hover:bg-indigo-700'
                  }`}
                >
                  Test with New Image
                </button>
                
                {prediction && (
                  <div className="mt-4 p-3 bg-indigo-100 rounded">
                    <h6 className="font-semibold text-indigo-800">Prediction Result:</h6>
                    <p className="text-sm text-indigo-700">
                      Category: <strong>{prediction.category}</strong>
                      <br />
                      Confidence: <strong>{prediction.confidence}%</strong>
                    </p>
                  </div>
                )}
                
                {!model && (
                  <p className="text-sm text-gray-500 mt-2">
                    Train a model first to make predictions
                  </p>
                )}
              </div>

              {/* Framework Side */}
              <div className="bg-purple-50 p-4 rounded-lg">
                <h5 className="font-semibold text-purple-800 mb-3">JavaScript Framework</h5>
                <p className="text-sm text-gray-600 mb-4">{frameworkComparison[3].framework}</p>
                
                <pre className="text-xs bg-gray-800 text-green-400 p-3 rounded overflow-x-auto">
{`function PredictionInterface() {
  const [prediction, setPrediction] = useState(null);
  
  const handlePredict = async () => {
    const result = await model.predict(newData);
    setPrediction(result);
  };
  
  return (
    <div>
      <button onClick={handlePredict}>
        Make Prediction
      </button>
      {prediction && (
        <div>Result: {prediction.category}</div>
      )}
    </div>
  );
}`}
                </pre>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Summary */}
      <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg">
        <h4 className="font-semibold mb-2">Key Insight:</h4>
        <p className="text-sm text-gray-700">
          Just as Teachable Machine abstracts away the complexity of machine learning, 
          JavaScript frameworks abstract away the complexity of web development. 
          Both let you focus on <strong>what you want to build</strong> rather than 
          <strong>how to build it</strong>.
        </p>
      </div>
    </div>
  );
};

export default TeachableMachineDemo;