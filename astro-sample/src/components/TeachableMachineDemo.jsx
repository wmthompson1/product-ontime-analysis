import { useState } from 'react';

export default function TeachableMachineDemo() {
  const [currentStep, setCurrentStep] = useState(1);
  const [images, setImages] = useState([]);
  const [isTraining, setIsTraining] = useState(false);
  const [model, setModel] = useState(null);

  const steps = [
    { id: 1, title: "Gather", description: "Collect training images for each class" },
    { id: 2, title: "Train", description: "Train your machine learning model" },
    { id: 3, title: "Export", description: "Use your trained model" }
  ];

  const handleAddImage = (className) => {
    const newImage = {
      id: Date.now(),
      class: className,
      src: `https://via.placeholder.com/100x100/4ade80/ffffff?text=${className}`
    };
    setImages([...images, newImage]);
  };

  const handleTrain = () => {
    setIsTraining(true);
    setTimeout(() => {
      setIsTraining(false);
      setModel({ accuracy: 0.95, created: new Date() });
      setCurrentStep(3);
    }, 3000);
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex justify-center mb-8">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-center">
            <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${
              currentStep >= step.id 
                ? 'bg-blue-600 border-blue-600 text-white' 
                : 'border-gray-300 text-gray-400'
            }`}>
              {step.id}
            </div>
            <div className="ml-3 mr-8">
              <div className={`text-sm font-medium ${
                currentStep >= step.id ? 'text-blue-600' : 'text-gray-400'
              }`}>
                {step.title}
              </div>
              <div className="text-xs text-gray-500">{step.description}</div>
            </div>
            {index < steps.length - 1 && (
              <div className={`w-16 h-1 ${
                currentStep > step.id ? 'bg-blue-600' : 'bg-gray-200'
              }`} />
            )}
          </div>
        ))}
      </div>

      {currentStep === 1 && (
        <div>
          <h3 className="text-xl font-bold mb-4">Step 1: Gather Training Data</h3>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6">
              <h4 className="font-semibold mb-2">Class A Images ({images.filter(img => img.class === 'A').length})</h4>
              <div className="grid grid-cols-4 gap-2 mb-4">
                {images.filter(img => img.class === 'A').map(img => (
                  <img key={img.id} src={img.src} alt="Class A" className="w-full h-16 object-cover rounded" />
                ))}
              </div>
              <button 
                onClick={() => handleAddImage('A')}
                className="w-full bg-green-600 text-white py-2 rounded hover:bg-green-700"
              >
                Add Image
              </button>
            </div>
            
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6">
              <h4 className="font-semibold mb-2">Class B Images ({images.filter(img => img.class === 'B').length})</h4>
              <div className="grid grid-cols-4 gap-2 mb-4">
                {images.filter(img => img.class === 'B').map(img => (
                  <img key={img.id} src={img.src} alt="Class B" className="w-full h-16 object-cover rounded" />
                ))}
              </div>
              <button 
                onClick={() => handleAddImage('B')}
                className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
              >
                Add Image
              </button>
            </div>
          </div>
          
          {images.length >= 4 && (
            <div className="text-center mt-6">
              <button 
                onClick={() => setCurrentStep(2)}
                className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
              >
                Continue to Training →
              </button>
            </div>
          )}
        </div>
      )}

      {currentStep === 2 && (
        <div className="text-center">
          <h3 className="text-xl font-bold mb-4">Step 2: Train Your Model</h3>
          <div className="mb-6">
            <p className="text-gray-600 mb-4">
              Ready to train with {images.length} images ({images.filter(img => img.class === 'A').length} Class A, {images.filter(img => img.class === 'B').length} Class B)
            </p>
            {!isTraining && !model && (
              <button 
                onClick={handleTrain}
                className="bg-orange-600 text-white px-8 py-3 rounded-lg hover:bg-orange-700 text-lg"
              >
                🚀 Train Model
              </button>
            )}
            
            {isTraining && (
              <div className="flex flex-col items-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mb-4"></div>
                <p className="text-orange-600 font-semibold">Training in progress...</p>
                <p className="text-sm text-gray-500">This usually takes a few minutes</p>
              </div>
            )}
          </div>
        </div>
      )}

      {currentStep === 3 && model && (
        <div className="text-center">
          <h3 className="text-xl font-bold mb-4">Step 3: Model Ready!</h3>
          <div className="bg-green-50 border border-green-200 rounded-lg p-6 mb-6">
            <div className="text-green-800">
              <div className="font-semibold text-lg mb-2">✅ Training Complete!</div>
              <div className="text-sm">
                Model Accuracy: {Math.round(model.accuracy * 100)}%<br/>
                Training Time: {new Date(model.created).toLocaleTimeString()}
              </div>
            </div>
          </div>
          
          <div className="grid md:grid-cols-3 gap-4 text-sm">
            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="font-semibold text-blue-800">Download</div>
              <div className="text-blue-600">Save your trained model</div>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <div className="font-semibold text-purple-800">Cloud API</div>
              <div className="text-purple-600">Use via REST API</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="font-semibold text-gray-800">Embed</div>
              <div className="text-gray-600">Add to your website</div>
            </div>
          </div>
          
          <button 
            onClick={() => {
              setCurrentStep(1);
              setImages([]);
              setModel(null);
            }}
            className="mt-6 bg-gray-600 text-white px-6 py-2 rounded hover:bg-gray-700"
          >
            Start Over
          </button>
        </div>
      )}
    </div>
  );
}